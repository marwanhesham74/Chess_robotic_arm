"""Print example 64-cell input payload. Run: python examples/make_vision_json.py"""
import json
import time
import uuid
import chess
from chess_brain_handover import cell_to_square

board = chess.Board()
cells = []
for row in range(8):
    for col in range(8):
        piece = board.piece_at(chess.parse_square(cell_to_square(row, col)))
        cells.append({"row": row, "col": col, "piece": piece.symbol() if piece else ".",
                      "confidence": 0.99})
payload = {
    "schema_version": "1.0", "capture_id": uuid.uuid4().hex,
    "source": "overhead_camera", "captured_at": time.time(),
    "orientation": "a8_top_left", "stable": True, "calibrated": True,
    "confidence": 0.99, "cells": cells,
}
print(json.dumps(payload, indent=2))
