"""ROS2 Auto Game Coordinator: starts PASSIVE. No physical actuation.

Subscribes to current chess state, single-camera board, robot safety gate
and brain events. When explicitly enabled, issues only the high-level
{"action":"sync"} and {"action":"next"} commands. No mock data, ack,
joint controls, reset or robot-safety decisions are ever synthesized.
"""
import json
import time

from .policy import can_arm_safety, can_request_next, can_request_sync


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Bool, String

    class AutoCoordinator(Node):
        def __init__(self):
            super().__init__('chess_auto_coordinator')
            self.declare_parameter('enabled', False)
            self.declare_parameter('max_message_age_s', 4.5)
            self.declare_parameter('sync_retry_interval_s', 2.0)
            self.state = None
            self.state_arrival = 0.0
            self.vision_capture = None
            self.vision_arrival = 0.0
            self.last_sync_capture = None
            self.last_sync_attempt = 0.0
            self.in_flight = None
            self.in_flight_since = 0.0
            self.safety_for_ply = None
            self.last_requested_ply = None
            self.enabled_last_tick = False
            self.pub_command = self.create_publisher(String, '/chess/command', 10)
            self.pub_status = self.create_publisher(String, '/chess/auto/status', 10)
            self.create_subscription(String, '/chess/state', self.on_state, 10)
            self.create_subscription(String, '/chess/events', self.on_event, 10)
            self.create_subscription(String, '/chess/vision/board', self.on_vision, 10)
            self.create_subscription(Bool, '/chess/safety_ready', self.on_safety, 10)
            self.create_timer(0.5, self.tick)
            self.create_timer(2.0, self.publish_status)
            self.get_logger().info('Auto coordinator launched PASSIVE by default. '
                                   'No commands without explicit enable + real vision and safety.')

        def decode(self, msg):
            try:
                result = json.loads(msg.data)
            except (TypeError, ValueError):
                return None
            return result if isinstance(result, dict) else None

        def on_state(self, msg):
            obj = self.decode(msg)
            if obj is not None:
                self.state = obj
                self.state_arrival = time.monotonic()
                if obj.get('pending_plan_id') is not None:
                    self.safety_for_ply = None
                    if self.in_flight == 'next':
                        self.in_flight = None
                if obj.get('synchronized') is True and self.in_flight == 'sync':
                    self.in_flight = None
                if obj.get('blocked') or obj.get('result') is not None:
                    self.safety_for_ply = None

        def on_vision(self, msg):
            obj = self.decode(msg)
            if (obj is not None and isinstance(obj.get('cells'), list) and
                    len(obj['cells']) == 64 and obj.get('stable') is True and
                    obj.get('calibrated') is True and
                    isinstance(obj.get('capture_id'), str) and obj.get('capture_id')):
                # Only freshness and frame presence. Chess Brain checks
                # full schema, confidence, content and actual timestamps.
                self.vision_capture = obj['capture_id']
                self.vision_arrival = time.monotonic()

        def on_safety(self, msg):
            # No latched/pending/moving safety assertion can authorize a
            # future ply. Only a NEW true while idle arms a matching ply.
            if not msg.data:
                self.safety_for_ply = None
            elif can_arm_safety(self.state):
                self.safety_for_ply = self.state['committed_plies']

        def on_event(self, msg):
            event = self.decode(msg)
            if not event:
                return
            if event.get('event') in ('command_response', 'command_error'):
                if event.get('action') == self.in_flight:
                    self.in_flight = None
                elif event.get('event') == 'command_error':
                    # ROS bridge command_error might have no action.
                    self.in_flight = None

        def send_command(self, action):
            msg = String()
            msg.data = json.dumps({'action': action})
            self.pub_command.publish(msg)
            self.in_flight = action
            self.in_flight_since = time.monotonic()
            self.get_logger().info('High-level chess command issued: %s' % action)

        def tick(self):
            now = time.monotonic()
            enabled = self.get_parameter('enabled').value is True
            if not enabled:
                if self.enabled_last_tick:
                    self.get_logger().warn('Auto mode disabled; pending robot plans are NOT cancelled. '
                                           'Use independent safety interlock if needed.')
                self.safety_for_ply = None
                self.in_flight = None
                self.enabled_last_tick = False
                return
            if not self.enabled_last_tick:
                # Require safety to be asserted AFTER activation.
                self.safety_for_ply = None
                self.last_requested_ply = None
                self.enabled_last_tick = True
                self.get_logger().warn('Auto mode enabled: requires genuine vision + independent safety signals')
            max_age = float(self.get_parameter('max_message_age_s').value)
            sync_interval = float(self.get_parameter('sync_retry_interval_s').value)
            if max_age <= 0 or sync_interval <= 0:
                self.get_logger().error('Invalid coordinator timing parameters; no command sent')
                return
            state_age = now - self.state_arrival if self.state_arrival else float('inf')
            vision_age = now - self.vision_arrival if self.vision_arrival else float('inf')
            # If the downstream bridge does not answer, do not blindly retry
            # a `next` command and risk a duplicate physical plan.
            if self.in_flight is not None:
                if now - self.in_flight_since > 8.0:
                    self.get_logger().error('Chess command response timeout (%s); '
                                            'automatic commands halted until explicit re-enable' % self.in_flight)
                    self.in_flight = None
                    self.set_parameters([rclpy.parameter.Parameter(
                        'enabled', rclpy.Parameter.Type.BOOL, False)])
                return
            if can_request_sync(enabled=True, state=self.state,
                                vision_seen=self.vision_capture is not None,
                                vision_age_s=vision_age, state_age_s=state_age,
                                in_flight=False, max_age_s=max_age):
                if (self.vision_capture != self.last_sync_capture and
                        now - self.last_sync_attempt >= sync_interval):
                    self.last_sync_capture = self.vision_capture
                    self.last_sync_attempt = now
                    self.send_command('sync')
                return
            if can_request_next(enabled=True, state=self.state,
                                state_age_s=state_age, max_age_s=max_age,
                                safety_for_ply=self.safety_for_ply,
                                last_requested_ply=self.last_requested_ply,
                                in_flight=False):
                self.last_requested_ply = self.state['committed_plies']
                self.safety_for_ply = None
                self.send_command('next')

        def publish_status(self):
            msg = String()
            msg.data = json.dumps({
                'enabled': self.get_parameter('enabled').value is True,
                'mode': 'armed' if self.get_parameter('enabled').value is True else 'passive',
                'brain_state_seen': self.state is not None,
                'vision_seen': self.vision_capture is not None,
                'safety_for_ply': self.safety_for_ply,
                'last_requested_ply': self.last_requested_ply,
                'command_in_flight': self.in_flight,
                'note': 'Coordinator does not operate robot joints or issue fake acknowledgements',
            }, separators=(',', ':'))
            self.pub_status.publish(msg)

    rclpy.init(args=args)
    node = AutoCoordinator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
