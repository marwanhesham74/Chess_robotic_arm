"""Run without ROS 2 or Stockfish: python3 -m unittest discover -s tests -v."""
import unittest

from chess_auto_coordinator.policy import can_arm_safety, can_request_next, can_request_sync


class TestCoordinatorPolicy(unittest.TestCase):
    def setUp(self):
        self.s = dict(synchronized=True, blocked=False, result=None,
                      pending_plan_id=None, robot_ack_received=False,
                      committed_plies=0)

    def next(self, **overrides):
        params = dict(enabled=True, state=self.s, state_age_s=0.2,
                      max_age_s=4.5, safety_for_ply=0,
                      last_requested_ply=None, in_flight=False)
        params.update(overrides)
        return can_request_next(**params)

    def test_disabled_is_passive(self):
        self.assertFalse(self.next(enabled=False))

    def test_requires_safety(self):
        self.assertFalse(self.next(safety_for_ply=None))

    def test_rejects_stale_safety_epoch(self):
        self.s['committed_plies'] = 1
        self.assertFalse(self.next(safety_for_ply=0))

    def test_rejects_duplicate_next_for_same_ply(self):
        self.assertFalse(self.next(last_requested_ply=0))

    def test_rejects_pending(self):
        self.s['pending_plan_id'] = 'abc'
        self.assertFalse(self.next())

    def test_rejects_blocked(self):
        self.s['blocked'] = True
        self.assertFalse(self.next())

    def test_rejects_game_over(self):
        self.s['result'] = '1-0'
        self.assertFalse(self.next())

    def test_rejects_unsynced(self):
        self.s['synchronized'] = False
        self.assertFalse(self.next())

    def test_rejects_expired_state(self):
        self.assertFalse(self.next(state_age_s=9.0))

    def test_next_allowed_when_all_gates_pass(self):
        self.assertTrue(self.next())

    def test_arming_requires_idle(self):
        self.assertTrue(can_arm_safety(self.s))
        self.s['pending_plan_id'] = 'abc'
        self.assertFalse(can_arm_safety(self.s))

    def test_sync_needs_vision_and_enabled(self):
        params = dict(enabled=True, state={**self.s, 'synchronized': False},
                      vision_seen=True, vision_age_s=0.2,
                      state_age_s=0.2, in_flight=False, max_age_s=4.5)
        self.assertTrue(can_request_sync(**params))
        self.assertFalse(can_request_sync(**{**params, 'vision_seen': False}))
        self.assertFalse(can_request_sync(**{**params, 'enabled': False}))
        self.assertFalse(can_request_sync(**{**params, 'vision_age_s': 5.0}))


if __name__ == '__main__':
    unittest.main()
