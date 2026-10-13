"""Optional ROS 2 Jazzy JSON bridge. Requires rclpy / std_msgs installed via ROS.

Every input is untrusted; this high-level node is NOT a motor/physical safety interlock.
See docs/INTEGRATION_CONTRACT.md for topic names and publisher responsibilities.
"""
import json
import os

from .core import GameController


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Bool, String

    class ChessBrainNode(Node):
        def __init__(self):
            super().__init__("chess_brain")
            self.declare_parameter("white_preset", "strong")
            self.declare_parameter("black_preset", "medium")
            self.declare_parameter("engine_path", "")
            self.declare_parameter("min_confidence", 0.95)
            self.declare_parameter("min_cell_confidence", 0.90)
            self.declare_parameter("allow_placement_shortcut", False)
            path = self.get_parameter("engine_path").value or os.environ.get("STOCKFISH_PATH") or None
            self.game = GameController(
                white=self.get_parameter("white_preset").value,
                black=self.get_parameter("black_preset").value,
                engine_path=path,
                min_confidence=float(self.get_parameter("min_confidence").value),
                min_cell_confidence=float(self.get_parameter("min_cell_confidence").value),
            )
            self.last_vision = None
            self.safety_ready = False  # must be asserted by EXTERNAL safety coordinator
            self.pub_plan = self.create_publisher(String, "/chess/move_plan", 10)
            self.pub_state = self.create_publisher(String, "/chess/state", 10)
            self.pub_events = self.create_publisher(String, "/chess/events", 10)
            self.create_subscription(String, "/chess/command", self.on_command, 10)
            self.create_subscription(String, "/chess/vision/board", self.on_vision, 10)
            self.create_subscription(String, "/chess/robot_ack", self.on_robot_ack, 10)
            self.create_subscription(Bool, "/chess/safety_ready", self.on_safety, 10)
            self.create_timer(2.0, self.publish_state)
            self.publish_state()
            self.get_logger().info("Chess Brain bridge started; waiting for initial vision sync + safety ready")

        def send(self, publisher, payload):
            msg = String()
            msg.data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            publisher.publish(msg)

        def publish_state(self):
            self.send(self.pub_state, self.game.state())

        def event(self, payload):
            self.send(self.pub_events, payload)
            self.publish_state()

        def parse(self, msg):
            value = json.loads(msg.data)
            if not isinstance(value, dict):
                raise ValueError("Expected a JSON object")
            return value

        def on_safety(self, msg):
            self.safety_ready = bool(msg.data)
            self.event({"event": "safety_signal", "ready": self.safety_ready})

        def on_command(self, msg):
            try:
                data = self.parse(msg)
                action = data.get("action")
                if action == "state":
                    self.publish_state()
                    return
                if action == "sync":
                    if self.last_vision is None:
                        response = {"ok": False, "status": "no_vision_received"}
                    else:
                        response = self.game.sync_initial_board(self.last_vision)
                elif action == "next":
                    if not self.safety_ready:
                        response = {"ok": False, "status": "waiting_for_safety_ready"}
                    else:
                        plan = self.game.next_plan()
                        self.safety_ready = False  # must rearm for every new move
                        self.send(self.pub_plan, plan.to_dict())
                        response = {"ok": True, "status": "plan_published", "plan_id": plan.plan_id}
                elif action == "manual":
                    if not self.safety_ready:
                        response = {"ok": False, "status": "waiting_for_safety_ready"}
                    else:
                        plan = self.game.manual_move(data["from_sq"], data["to_sq"], data.get("promotion"))
                        self.safety_ready = False
                        self.send(self.pub_plan, plan.to_dict())
                        response = {"ok": True, "status": "manual_plan_published", "plan_id": plan.plan_id}
                elif action == "reset":
                    if not self.safety_ready:
                        response = {"ok": False, "status": "waiting_for_safety_ready"}
                    else:
                        self.game.reset(physical_reset_confirmed=data.get("physical_reset_confirmed") is True,
                                        fen=data.get("fen"))
                        self.safety_ready = False
                        self.last_vision = None
                        response = {"ok": True, "status": "reset_requires_new_vision_sync"}
                else:
                    response = {"ok": False, "status": "unknown_command"}
                self.event({"event": "command_response", "action": action, **response})
            except (Exception) as exc:
                self.event({"event": "command_error", "ok": False, "error": str(exc)})

        def on_robot_ack(self, msg):
            try:
                data = self.parse(msg)
                response = self.game.robot_ack(
                    data["plan_id"], success=data.get("success") is True,
                    arm_parked=data.get("arm_parked") is True,
                    gripper_released=data.get("gripper_released") is True,
                )
                self.event({"event": "robot_ack_response", **response})
            except Exception as exc:
                self.event({"event": "robot_ack_error", "ok": False, "error": str(exc)})

        def on_vision(self, msg):
            try:
                data = self.parse(msg)
                if "cells" not in data and not bool(self.get_parameter("allow_placement_shortcut").value):
                    raise ValueError("ROS live vision requires a 64-cell board; placement shortcut disabled")
                self.last_vision = data
                if self.game.pending is not None and self.game.ack_received_at is not None:
                    result = self.game.confirm_vision(data)
                    if result.get("status") == "committed":
                        self.safety_ready = False  # demand fresh coordinator readiness after commit
                    # Publish informative results; do not endlessly broadcast transient invalid frames.
                    if result["status"] not in ("duplicate_capture_id", "observation_before_robot_ack"):
                        self.event({"event": "vision_confirmation", **result})
            except Exception as exc:
                self.event({"event": "vision_input_error", "ok": False, "error": str(exc)})

        def destroy_node(self):
            self.game.close()
            return super().destroy_node()

    rclpy.init(args=args)
    node = None
    try:
        node = ChessBrainNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
