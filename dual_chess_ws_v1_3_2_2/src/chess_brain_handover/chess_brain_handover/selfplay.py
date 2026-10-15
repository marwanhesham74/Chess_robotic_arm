"""Software-only self play: fake camera and fake robot, NEVER use as live robot ack."""
import argparse
import csv
import json
from pathlib import Path
import time
import uuid

from .core import GameController, ORIENTATION, SCHEMA_VERSION


def fake_vision(placement):
    return {
        "schema_version": SCHEMA_VERSION, "capture_id": uuid.uuid4().hex,
        "source": "SIMULATED_PERFECT_CAMERA", "captured_at": time.time(),
        "stable": True, "calibrated": True, "confidence": 1.0,
        "orientation": ORIENTATION, "piece_placement": placement,
    }


def run(white, black, engine_path, max_plies, output):
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    records = []
    errors = []
    result = None
    reason = "max_plies_reached"
    with GameController(white=white, black=black, engine_path=engine_path) as game:
        init = game.sync_initial_board(fake_vision(game.board.board_fen()))
        if not init["ok"]:
            raise RuntimeError(init)
        for ply in range(max_plies):
            if game.result() is not None:
                reason = "game_over"
                break
            try:
                plan = game.next_plan()
                ack = game.robot_ack(plan.plan_id, success=True, arm_parked=True,
                                     gripper_released=True)
                if not ack["ok"]:
                    raise RuntimeError(ack)
                confirmed = game.confirm_vision(fake_vision(plan.expected_fen.split()[0]))
                if not confirmed["ok"]:
                    raise RuntimeError(confirmed)
                records.append(game.export_history()[-1])
                print(f"{ply + 1:3d} {plan.side:5s} {plan.san:7s} {plan.uci} {plan.think_ms:.1f}ms")
            except Exception as exc:
                errors.append({"ply": ply + 1, "error": str(exc)})
                reason = "error"
                break
        if game.result() is not None:
            reason = "game_over"
        result = game.result()
    fields = ["plan_id", "side", "uci", "san", "before_fen", "after_fen", "eval_cp", "think_ms", "capture_id"]
    with (output / "moves.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    thoughts = [r["think_ms"] for r in records if r["think_ms"] is not None]
    summary = {
        "mode": "SIMULATED_PERFECT_VISION_AND_EXECUTION",
        "white_preset": white, "black_preset": black, "result": result,
        "stop_reason": reason, "plies_committed": len(records),
        "average_think_ms": round(sum(thoughts) / len(thoughts), 2) if thoughts else None,
        "max_think_ms": round(max(thoughts), 2) if thoughts else None,
        "elapsed_wall_s": round(time.perf_counter() - started, 2), "errors": errors,
        "notice": "Not a camera, ROS execution, safety, or hardware validation test. A ply cutoff is NOT a draw."
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--white", choices=["easy", "medium", "strong", "max"], default="strong")
    p.add_argument("--black", choices=["easy", "medium", "strong", "max"], default="medium")
    p.add_argument("--engine-path", default=None)
    p.add_argument("--max-plies", type=int, default=80)
    p.add_argument("--output", type=Path, default=Path("results/selfplay"))
    a = p.parse_args()
    if a.max_plies < 1:
        p.error("--max-plies must be > 0")
    raise SystemExit(run(a.white, a.black, a.engine_path, a.max_plies, a.output))


if __name__ == "__main__":
    main()
