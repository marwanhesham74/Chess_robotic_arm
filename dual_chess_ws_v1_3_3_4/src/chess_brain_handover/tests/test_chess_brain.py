"""Run: python -m unittest discover -s tests -v  (requires python-chess)."""
import time
import unittest
import uuid

import chess

from chess_brain_handover import (
    BusyError, GameBlocked, GameController, IllegalMove, Observation,
    cell_to_square, describe_move, placement_from_cells, square_to_cell,
)


class FirstLegalPlayer:
    def choose_move(self, board):
        return next(iter(board.legal_moves)), None, 0.01

    def close(self):
        pass


def game(**opts):
    return GameController(players={chess.WHITE: FirstLegalPlayer(),
                                   chess.BLACK: FirstLegalPlayer()}, **opts)


def camera(placement, **overrides):
    value = {
        "schema_version": "1.0", "capture_id": uuid.uuid4().hex,
        "source": "unit_test_camera", "captured_at": time.time(),
        "stable": True, "calibrated": True, "confidence": 0.99,
        "orientation": "a8_top_left", "piece_placement": placement,
    }
    value.update(overrides)
    return value


def ready_game(**kwargs):
    g = game(**kwargs)
    resp = g.sync_initial_board(camera(g.board.board_fen()))
    assert resp["ok"], resp
    return g


def confirmed(g, plan):
    ack = g.robot_ack(plan.plan_id, success=True, arm_parked=True, gripper_released=True)
    if not ack["ok"]:
        return ack
    return g.confirm_vision(camera(plan.expected_fen.split()[0]))


class ContractTest(unittest.TestCase):
    def test_square_conversion(self):
        for s in ("a8", "h8", "a1", "h1", "e4", "e2"):
            v = square_to_cell(s)
            self.assertEqual(cell_to_square(v["row"], v["col"]), s)
        self.assertEqual(square_to_cell("e4"), {"row": 4, "col": 4})
        self.assertEqual(square_to_cell("e2"), {"row": 6, "col": 4})

    def test_reject_bad_cells(self):
        with self.assertRaises(ValueError):
            placement_from_cells([])
        bad = [{"row": 0, "col": 0, "piece": ".", "confidence": 1.0}] * 64
        with self.assertRaises(ValueError):
            placement_from_cells(bad)

    def test_complete_cells_valid(self):
        cells = []
        b = chess.Board()
        for row in range(8):
            for col in range(8):
                sq = cell_to_square(row, col)
                piece = b.piece_at(chess.parse_square(sq))
                cells.append({"row": row, "col": col,
                              "piece": piece.symbol() if piece else ".", "confidence": 0.98})
        payload = camera(b.board_fen())
        del payload["piece_placement"]
        payload["cells"] = cells
        obs = Observation.from_dict(payload)
        self.assertEqual(obs.piece_placement, b.board_fen())
        self.assertEqual(obs.min_cell_confidence, 0.98)

    def test_bad_orientation_rejected(self):
        with self.assertRaises(ValueError):
            Observation.from_dict(camera(chess.Board().board_fen(), orientation="h8_top_left"))

    def test_unstable_rejected(self):
        with game() as g:
            self.assertFalse(g.sync_initial_board(camera(g.board.board_fen(), stable=False))["ok"])

    def test_weak_confidence_rejected(self):
        with game() as g:
            self.assertEqual(g.sync_initial_board(camera(g.board.board_fen(), confidence=0.4))["status"],
                             "unreliable_observation")

    def test_old_frame_rejected(self):
        with game() as g:
            result = g.sync_initial_board(camera(g.board.board_fen(), captured_at=time.time()-999))
            self.assertEqual(result["status"], "stale_or_future_observation")


class ChessCoreTest(unittest.TestCase):
    def test_must_sync_before_planning(self):
        with game() as g:
            with self.assertRaises(GameBlocked):
                g.next_plan()

    def test_sync_wrong_board_fails(self):
        with game() as g:
            self.assertEqual(g.sync_initial_board(camera("8/8/8/8/8/8/8/8"))["status"], "initial_board_mismatch")

    def test_20_legal_opening_moves(self):
        with ready_game() as g:
            self.assertEqual(len(g.state()["legal_moves"]), 20)

    def test_pending_prevents_double_plan(self):
        with ready_game() as g:
            initial = g.board.fen()
            p = g.manual_move("e2", "e4")
            self.assertEqual(g.board.fen(), initial)
            with self.assertRaises(BusyError):
                g.next_plan()
            self.assertEqual(p.to_dict()["from_cell"], {"row": 6, "col": 4})
            self.assertEqual(p.to_dict()["to_cell"], {"row": 4, "col": 4})

    def test_cannot_commit_before_ack(self):
        with ready_game() as g:
            p = g.manual_move("e2", "e4")
            self.assertEqual(g.confirm_vision(camera(p.expected_fen))["status"], "awaiting_robot_ack")
            self.assertEqual(g.state()["committed_plies"], 0)

    def test_ack_requires_park_and_release(self):
        with ready_game() as g:
            p = g.next_plan()
            res = g.robot_ack(p.plan_id, success=True, arm_parked=False, gripper_released=True)
            self.assertEqual(res["status"], "blocked")
            with self.assertRaises(GameBlocked):
                g.next_plan()

    def test_stale_id_is_rejected(self):
        with ready_game() as g:
            p = g.manual_move("e2", "e4")
            self.assertEqual(g.robot_ack("wrong", success=True, arm_parked=True,
                                         gripper_released=True)["status"], "stale_plan_id")
            self.assertEqual(g.state()["committed_plies"], 0)

    def test_reject_pre_ack_camera_frame(self):
        with ready_game() as g:
            p = g.manual_move("e2", "e4")
            earlier = camera(p.expected_fen, captured_at=time.time()-0.1)
            g.robot_ack(p.plan_id, success=True, arm_parked=True, gripper_released=True)
            self.assertEqual(g.confirm_vision(earlier)["status"], "observation_before_robot_ack")

    def test_valid_commit_changes_turn(self):
        with ready_game() as g:
            p = g.manual_move("e2", "e4")
            self.assertTrue(confirmed(g, p)["ok"])
            self.assertEqual(g.state()["turn"], "black")
            self.assertEqual(g.state()["committed_plies"], 1)

    def test_mismatch_duplicate_capture_not_counted_twice(self):
        with ready_game() as g:
            p = g.manual_move("e2", "e4")
            g.robot_ack(p.plan_id, success=True, arm_parked=True, gripper_released=True)
            wrong = camera(g.board.board_fen())
            a = g.confirm_vision(wrong)
            b = g.confirm_vision(wrong)
            self.assertEqual(a["status"], "vision_mismatch")
            self.assertEqual(b["status"], "duplicate_capture_id")
            self.assertEqual(g.mismatches, 1)

    def test_three_unique_mismatches_block(self):
        with ready_game() as g:
            p = g.manual_move("e2", "e4")
            g.robot_ack(p.plan_id, success=True, arm_parked=True, gripper_released=True)
            for i in range(3):
                last = g.confirm_vision(camera(g.board.board_fen()))
            self.assertEqual(last["status"], "blocked")
            self.assertEqual(g.state()["committed_plies"], 0)

    def test_manual_illegal_move_rejected(self):
        with ready_game() as g:
            with self.assertRaises(IllegalMove):
                g.manual_move("e2", "e5")

    def test_castling_moves_both_king_and_rook(self):
        with game() as g:
            g.reset(fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
                    physical_reset_confirmed=True)
            g.sync_initial_board(camera(g.board.board_fen()))
            p = g.manual_move("e1", "g1")
            self.assertTrue(p.is_castling)
            self.assertEqual([(a.kind, a.source, a.target) for a in p.actions],
                             [("move", "e1", "g1"), ("move", "h1", "f1")])

    def test_en_passant_removes_from_correct_cell(self):
        with game() as g:
            g.reset(fen="4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
                    physical_reset_confirmed=True)
            g.sync_initial_board(camera(g.board.board_fen()))
            p = g.manual_move("e5", "d6")
            self.assertEqual(p.capture_sq, "d5")
            self.assertEqual(p.actions[0].kind, "remove")

    def test_promotion_requests_spare_piece(self):
        with game() as g:
            g.reset(fen="4k3/P7/8/8/8/8/8/4K3 w - - 0 1", physical_reset_confirmed=True)
            g.sync_initial_board(camera(g.board.board_fen()))
            p = g.manual_move("a7", "a8", "q")
            self.assertEqual(p.uci, "a7a8q")
            self.assertEqual(p.actions[-1].kind, "promote")

    def test_full_white_black_turn_sequence(self):
        with ready_game() as g:
            for _ in range(8):
                p = g.next_plan()
                self.assertTrue(confirmed(g, p)["ok"])
            self.assertEqual(len(g.export_history()), 8)
            self.assertEqual(g.export_history()[0]["side"], "white")
            self.assertEqual(g.export_history()[1]["side"], "black")

    def test_board_property_is_snapshot(self):
        with ready_game() as g:
            snapshot = g.board
            snapshot.clear_board()
            self.assertEqual(len(g.state()["legal_moves"]), 20)

    def test_reset_needs_operator_confirmation(self):
        with ready_game() as g:
            with self.assertRaises(GameBlocked):
                g.reset(physical_reset_confirmed=False)
            g.reset(physical_reset_confirmed=True)
            self.assertFalse(g.synchronized)


if __name__ == "__main__":
    unittest.main()
