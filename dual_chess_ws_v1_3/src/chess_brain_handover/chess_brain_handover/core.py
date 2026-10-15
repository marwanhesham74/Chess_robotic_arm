"""Chess engine + physical-world verification boundary for STANDARD chess.

NOT hardware safety software. A separate ROS/hardware safety controller MUST interlock
arms, guard workspaces, verify grippers, and keep the physical board calibrated.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import os
import shutil
import time
import uuid
from typing import Mapping, Optional, Protocol

import chess
import chess.engine

SCHEMA_VERSION = "1.0"
ORIENTATION = "a8_top_left"   # camera matrix row 0 = chess rank 8, col 0 = file a

PRESETS = {
    "easy": {"elo": 1350, "think_time": 0.2},
    "medium": {"elo": 1800, "think_time": 0.5},
    "strong": {"elo": 2400, "think_time": 1.0},
    "max": {"think_time": 3.0, "threads": 4, "hash_mb": 512},
}


class IllegalMove(ValueError):
    """An illegal chess move was requested."""


class BusyError(RuntimeError):
    """Cannot plan again while a plan awaits verification."""


class GameBlocked(RuntimeError):
    """The game cannot continue without operator or coordinator action."""


def square_to_cell(square: str) -> dict:
    """Chess e4 -> image row=4, col=4; a8 -> (0,0)."""
    idx = chess.parse_square(square.lower())
    return {"row": 7 - chess.square_rank(idx), "col": chess.square_file(idx)}


def cell_to_square(row: int, col: int) -> str:
    if type(row) is not int or type(col) is not int or not (0 <= row < 8 and 0 <= col < 8):
        raise ValueError("row and col must be integers from 0 through 7")
    return chess.square_name(chess.square(col, 7 - row))


def _finite_score(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _placement(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("piece_placement must be a FEN placement string")
    fields = value.strip().split()
    if len(fields) == 6:
        chess.Board(value)  # validate supplied six-field FEN syntax
    elif len(fields) != 1:
        raise ValueError("Expected one-field placement or six-field FEN")
    board = chess.Board(None)
    board.set_board_fen(fields[0])
    return board.board_fen()


def placement_from_cells(cells: list[dict]) -> tuple[str, float]:
    """Read an EXPLICIT observation for each of 64 cells, including empty ones.

    piece is a FEN symbol (PNBRQK/pnbrqk) or '.' / null for empty.
    Returns placement and minimum cell confidence.
    """
    if not isinstance(cells, list) or len(cells) != 64:
        raise ValueError("cells must contain exactly 64 square observations")
    board = chess.Board(None)
    seen = set()
    minimum = 1.0
    for cell in cells:
        if not isinstance(cell, dict):
            raise ValueError("each cell must be an object")
        sq = cell_to_square(cell.get("row"), cell.get("col"))
        if sq in seen:
            raise ValueError(f"duplicate camera cell: {sq}")
        seen.add(sq)
        score = _finite_score(cell.get("confidence"), "cell confidence")
        if not 0 <= score <= 1:
            raise ValueError("cell confidence must be between 0 and 1")
        minimum = min(minimum, score)
        piece = cell.get("piece")
        if piece in (None, "."):
            continue
        if not isinstance(piece, str) or len(piece) != 1 or piece not in "PNBRQKpnbrqk":
            raise ValueError(f"invalid chess piece at {sq}: {piece!r}")
        board.set_piece_at(chess.parse_square(sq), chess.Piece.from_symbol(piece))
    return board.board_fen(), minimum


@dataclass(frozen=True)
class Observation:
    capture_id: str
    source: str
    captured_at: float  # Unix wall clock seconds; synchronize camera and host clocks
    stable: bool
    calibrated: bool
    confidence: float
    piece_placement: str
    min_cell_confidence: float = 1.0

    @classmethod
    def from_dict(cls, payload: dict) -> "Observation":
        if not isinstance(payload, dict):
            raise ValueError("Vision payload must be a JSON object")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported schema_version")
        if payload.get("orientation") != ORIENTATION:
            raise ValueError("Expected orientation a8_top_left; calibrate/reorient in vision")
        if "cells" in payload and "piece_placement" in payload:
            raise ValueError("Send either cells or piece_placement, not both")
        if "cells" in payload:
            placement, minimum = placement_from_cells(payload["cells"])
        elif "piece_placement" in payload:
            placement, minimum = _placement(payload["piece_placement"]), 1.0
        else:
            raise ValueError("Missing cells or piece_placement")
        for field in ("capture_id", "source"):
            if not isinstance(payload.get(field), str) or not payload[field].strip():
                raise ValueError(f"Missing nonempty {field}")
        score = _finite_score(payload.get("confidence"), "confidence")
        timestamp = _finite_score(payload.get("captured_at"), "captured_at")
        if timestamp <= 0 or not 0 <= score <= 1:
            raise ValueError("Invalid timestamp or confidence")
        if type(payload.get("stable")) is not bool or type(payload.get("calibrated")) is not bool:
            raise ValueError("stable and calibrated must be bool")
        return cls(payload["capture_id"], payload["source"], timestamp,
                   payload["stable"], payload["calibrated"], score, placement, minimum)


@dataclass(frozen=True)
class Action:
    kind: str  # remove, move, promote
    source: Optional[str] = None
    target: Optional[str] = None
    piece: Optional[str] = None

    def to_dict(self) -> dict:
        result = asdict(self)
        if self.source is not None:
            result["source_cell"] = square_to_cell(self.source)
        if self.target is not None:
            result["target_cell"] = square_to_cell(self.target)
        return result


@dataclass(frozen=True)
class MovePlan:
    plan_id: str
    uci: str
    san: str
    side: str
    piece: str
    from_sq: str
    to_sq: str
    before_fen: str
    expected_fen: str
    actions: tuple[Action, ...]
    created_at: float
    captured: Optional[str] = None
    capture_sq: Optional[str] = None
    is_castling: bool = False
    promotion: Optional[str] = None
    gives_check: bool = False
    eval_cp: Optional[int] = None
    think_ms: Optional[float] = None

    def to_dict(self) -> dict:
        result = asdict(self)
        result["schema_version"] = SCHEMA_VERSION
        result["from_cell"] = square_to_cell(self.from_sq)
        result["to_cell"] = square_to_cell(self.to_sq)
        result["actions"] = [action.to_dict() for action in self.actions]
        return result


class Player(Protocol):
    def choose_move(self, board: chess.Board) -> tuple[chess.Move, Optional[int], float]: ...
    def close(self) -> None: ...


class StockfishPlayer:
    """Runs Stockfish through the python-chess UCI adapter."""

    def __init__(self, preset: str = "medium", engine_path: Optional[str] = None):
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset: {preset}")
        cfg = PRESETS[preset]
        self.think_time = float(cfg["think_time"])
        path = engine_path or os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish")
        if not path and os.path.isfile("/usr/games/stockfish"):
            path = "/usr/games/stockfish"
        if not path:
            raise FileNotFoundError("Stockfish not found. Install it or set STOCKFISH_PATH.")
        self.engine = chess.engine.SimpleEngine.popen_uci(path)
        try:
            opts = {}
            if "Threads" in self.engine.options:
                opts["Threads"] = cfg.get("threads", 2)
            if "Hash" in self.engine.options:
                opts["Hash"] = cfg.get("hash_mb", 128)
            if "elo" in cfg:
                if "UCI_LimitStrength" in self.engine.options:
                    opts["UCI_LimitStrength"] = True
                if "UCI_Elo" in self.engine.options:
                    elo_option = self.engine.options["UCI_Elo"]
                    elo = cfg["elo"]
                    if elo_option.min is not None:
                        elo = max(elo, elo_option.min)
                    if elo_option.max is not None:
                        elo = min(elo, elo_option.max)
                    opts["UCI_Elo"] = elo
            elif "UCI_LimitStrength" in self.engine.options:
                opts["UCI_LimitStrength"] = False
            self.engine.configure(opts)
        except Exception:
            self.engine.quit()
            raise

    def choose_move(self, board: chess.Board) -> tuple[chess.Move, Optional[int], float]:
        start = time.perf_counter()
        response = self.engine.play(board, chess.engine.Limit(time=self.think_time),
                                    info=chess.engine.INFO_SCORE)
        elapsed = (time.perf_counter() - start) * 1000
        if response.move is None:
            raise RuntimeError("Stockfish returned no chess move")
        score_obj = response.info.get("score")
        score = score_obj.pov(board.turn).score(mate_score=100000) if score_obj else None
        return response.move, score, elapsed

    def close(self) -> None:
        self.engine.quit()


def describe_move(board: chess.Board, move: chess.Move, *,
                  score: Optional[int] = None, think_ms: Optional[float] = None) -> MovePlan:
    """Convert a LEGAL chess move into logical pick/place instructions.

    Does not compute robot kinematics, collision paths, gripper force, bins, or timing.
    """
    if move not in board.legal_moves:
        raise IllegalMove(f"Illegal move: {move.uci()}")
    name = chess.square_name
    before = board.fen()
    piece = board.piece_at(move.from_square)
    actions: list[Action] = []
    captured = capture_sq = None
    if board.is_capture(move):
        if board.is_en_passant(move):
            cap_idx = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        else:
            cap_idx = move.to_square
        capture_sq = name(cap_idx)
        cap_piece = board.piece_at(cap_idx)
        captured = cap_piece.symbol() if cap_piece else None
        actions.append(Action("remove", source=capture_sq))
    actions.append(Action("move", source=name(move.from_square), target=name(move.to_square)))
    castling = board.is_castling(move)
    if castling:
        rank = chess.square_rank(move.from_square)
        kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
        source_file, target_file = ((7, 5) if kingside else (0, 3))
        actions.append(Action("move", source=name(chess.square(source_file, rank)),
                              target=name(chess.square(target_file, rank))))
    promoted = chess.piece_symbol(move.promotion) if move.promotion else None
    if promoted:
        actions.append(Action("promote", source=name(move.to_square),
                              target=name(move.to_square), piece=promoted))
    future = board.copy(stack=True)
    future.push(move)
    return MovePlan(
        plan_id=uuid.uuid4().hex, uci=move.uci(), san=board.san(move),
        side="white" if board.turn == chess.WHITE else "black", piece=piece.symbol(),
        from_sq=name(move.from_square), to_sq=name(move.to_square),
        before_fen=before, expected_fen=future.fen(), actions=tuple(actions),
        created_at=time.time(), captured=captured, capture_sq=capture_sq,
        is_castling=castling, promotion=promoted, gives_check=board.gives_check(move),
        eval_cp=score, think_ms=think_ms,
    )


class GameController:
    """Authoritative board, pending moves, independent execution/vision verification.

    NO robot control. No automatic resynchronization. No new plan until prior
    plan has been confirmed or an operator resets a verified physical board.
    """

    def __init__(self, white: str = "strong", black: str = "medium", *,
                 engine_path: Optional[str] = None,
                 players: Optional[Mapping[chess.Color, Player]] = None,
                 max_mismatches: int = 3,
                 min_confidence: float = 0.95,
                 min_cell_confidence: float = 0.90,
                 max_vision_age_s: float = 5.0):
        if max_mismatches < 1 or not (0 <= min_confidence <= 1) or not (0 <= min_cell_confidence <= 1):
            raise ValueError("Invalid verification limits")
        if max_vision_age_s <= 0:
            raise ValueError("max_vision_age_s must be positive")
        if players is not None:
            if set(players) != {chess.WHITE, chess.BLACK}:
                raise ValueError("players must include both chess colors")
            self.players = dict(players)
        else:
            white_player = StockfishPlayer(white, engine_path)
            try:
                black_player = StockfishPlayer(black, engine_path)
            except Exception:
                white_player.close()
                raise
            self.players = {chess.WHITE: white_player, chess.BLACK: black_player}
        self._board = chess.Board()
        self.pending: Optional[MovePlan] = None
        self.ack_received_at: Optional[float] = None
        self.synchronized = False
        self.blocked = False
        self.block_reason: Optional[str] = None
        self.max_mismatches = max_mismatches
        self.min_confidence = min_confidence
        self.min_cell_confidence = min_cell_confidence
        self.max_vision_age_s = max_vision_age_s
        self.mismatches = 0
        self.seen_capture_ids: set[str] = set()
        self.history: list[dict] = []
        self._closed = False

    def __enter__(self) -> "GameController":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            for player in self.players.values():
                player.close()

    @property
    def board(self) -> chess.Board:
        return self._board.copy(stack=True)

    def result(self) -> Optional[str]:
        result = self._board.outcome(claim_draw=True)
        return result.result() if result else None

    def state(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "fen": self._board.fen(),
            "turn": "white" if self._board.turn == chess.WHITE else "black",
            "result": self.result(), "synchronized": self.synchronized,
            "blocked": self.blocked, "block_reason": self.block_reason,
            "pending_plan_id": self.pending.plan_id if self.pending else None,
            "pending_move": self.pending.uci if self.pending else None,
            "robot_ack_received": self.ack_received_at is not None,
            "committed_plies": len(self.history),
            "legal_moves": [move.uci() for move in self._board.legal_moves],
        }

    def _parse_observation(self, observation: dict, *, after: Optional[float] = None) -> tuple[Optional[Observation], dict]:
        try:
            obs = Observation.from_dict(observation)
        except (ValueError, TypeError, KeyError, chess.InvalidMoveError) as exc:
            return None, {"ok": False, "status": "invalid_observation", "error": str(exc)}
        now = time.time()
        if obs.captured_at > now + 2.0 or now - obs.captured_at > self.max_vision_age_s:
            return None, {"ok": False, "status": "stale_or_future_observation"}
        if after is not None and obs.captured_at < after:
            return None, {"ok": False, "status": "observation_before_robot_ack"}
        if not obs.stable or not obs.calibrated or obs.confidence < self.min_confidence or obs.min_cell_confidence < self.min_cell_confidence:
            return None, {"ok": False, "status": "unreliable_observation"}
        return obs, {"ok": True}

    def sync_initial_board(self, observation: dict) -> dict:
        """Physical starting board MUST match expected board before requesting moves."""
        if self._closed or self.pending is not None or self.blocked:
            return {"ok": False, "status": "not_ready_for_sync"}
        obs, status = self._parse_observation(observation)
        if obs is None:
            return status
        if obs.piece_placement != self._board.board_fen():
            return {"ok": False, "status": "initial_board_mismatch",
                    "expected": self._board.board_fen(), "observed": obs.piece_placement}
        self.synchronized = True
        return {"ok": True, "status": "synchronized", "fen": self._board.fen()}

    def _ensure_ready(self) -> None:
        if self._closed:
            raise GameBlocked("Controller closed")
        if self.blocked:
            raise GameBlocked(f"Game blocked: {self.block_reason}")
        if not self.synchronized:
            raise GameBlocked("Vision must verify the physical board before planning")
        if self.pending is not None:
            raise BusyError("A plan is already pending; verify it first")
        if self.result() is not None:
            raise GameBlocked(f"Game finished: {self.result()}")

    def next_plan(self) -> MovePlan:
        self._ensure_ready()
        move, score, elapsed = self.players[self._board.turn].choose_move(self.board)
        self.pending = describe_move(self._board, move, score=score, think_ms=elapsed)
        self.ack_received_at = None
        self.seen_capture_ids.clear()
        self.mismatches = 0
        return self.pending

    def manual_move(self, from_sq: str, to_sq: str, promotion: Optional[str] = None) -> MovePlan:
        self._ensure_ready()
        try:
            from_idx = chess.parse_square(from_sq.lower())
            to_idx = chess.parse_square(to_sq.lower())
            piece = self._board.piece_at(from_idx)
            if piece and piece.piece_type == chess.PAWN and chess.square_rank(to_idx) in (0, 7):
                promotion = promotion or "q"  # default to queen for manual UI
            promotion_code = chess.PIECE_SYMBOLS.index(promotion.lower()) if promotion else None
            move = chess.Move(from_idx, to_idx, promotion=promotion_code)
        except (TypeError, ValueError, AttributeError) as exc:
            raise IllegalMove(f"Invalid move or promotion: {exc}") from exc
        self.pending = describe_move(self._board, move)
        self.ack_received_at = None
        self.seen_capture_ids.clear()
        self.mismatches = 0
        return self.pending

    def robot_ack(self, plan_id: str, *, success: bool, arm_parked: bool, gripper_released: bool) -> dict:
        """Explicit ack from robot coordinator, not an assumption derived from images."""
        if self.pending is None:
            return {"ok": False, "status": "no_pending_plan"}
        if plan_id != self.pending.plan_id:
            return {"ok": False, "status": "stale_plan_id"}
        if self.blocked:
            return {"ok": False, "status": "blocked"}
        if self.ack_received_at is not None:
            return {"ok": True, "status": "ack_already_received"}
        if not success or not arm_parked or not gripper_released:
            self.blocked = True
            self.block_reason = "robot_execution_failed_or_not_safe"
            return {"ok": False, "status": "blocked", "reason": self.block_reason}
        self.ack_received_at = time.time()
        return {"ok": True, "status": "awaiting_fresh_vision", "plan_id": plan_id}

    def confirm_vision(self, observation: dict) -> dict:
        """Commit when fresh, post-ack visual board matches plan.expected_fen.

        Repeated frame IDs do not consume mismatch retry budget.
        """
        if self.pending is None:
            return {"ok": False, "status": "no_pending_plan"}
        if self.blocked:
            return {"ok": False, "status": "blocked", "reason": self.block_reason}
        if self.ack_received_at is None:
            return {"ok": False, "status": "awaiting_robot_ack"}
        obs, status = self._parse_observation(observation, after=self.ack_received_at)
        if obs is None:
            return status
        if obs.capture_id in self.seen_capture_ids:
            return {"ok": False, "status": "duplicate_capture_id"}
        self.seen_capture_ids.add(obs.capture_id)
        expected = self.pending.expected_fen.split()[0]
        if obs.piece_placement != expected:
            self.mismatches += 1
            if self.mismatches >= self.max_mismatches:
                self.blocked = True
                self.block_reason = "repeated_vision_mismatch"
            return {"ok": False, "status": "blocked" if self.blocked else "vision_mismatch",
                    "expected": expected, "observed": obs.piece_placement,
                    "mismatches": self.mismatches}
        plan = self.pending
        if self._board.fen() != plan.before_fen:
            self.blocked = True
            self.block_reason = "internal_board_state_changed"
            raise GameBlocked(self.block_reason)
        self._board.push_uci(plan.uci)
        self.history.append({"plan_id": plan.plan_id, "side": plan.side, "uci": plan.uci,
                             "san": plan.san, "before_fen": plan.before_fen,
                             "after_fen": self._board.fen(), "eval_cp": plan.eval_cp,
                             "think_ms": plan.think_ms, "capture_id": obs.capture_id})
        self.pending = None
        self.ack_received_at = None
        self.mismatches = 0
        self.seen_capture_ids.clear()
        return {"ok": True, "status": "committed", "fen": self._board.fen(), "result": self.result()}

    def reset(self, *, physical_reset_confirmed: bool, fen: Optional[str] = None) -> None:
        """Explicit operator reset; physical board reset MUST be confirmed externally."""
        if not physical_reset_confirmed:
            raise GameBlocked("Cannot reset unless the physical board was reset and arms are safe")
        if self._closed:
            raise GameBlocked("Controller closed")
        board = chess.Board(fen) if fen else chess.Board()
        if not board.is_valid():
            raise ValueError("Invalid start chess position")
        self._board = board
        self.pending = None
        self.ack_received_at = None
        self.synchronized = False  # MUST obtain a fresh overhead observation again
        self.blocked = False
        self.block_reason = None
        self.mismatches = 0
        self.seen_capture_ids.clear()
        self.history = []

    def export_history(self) -> list[dict]:
        return [record.copy() for record in self.history]
