"""Chess Brain public API. Uses a private, pinned python-chess copy after build."""
from pathlib import Path as _Path
import sys as _sys

# Colcon installs ROS console scripts with /usr/bin/python3 on Ubuntu.
# Resolve our own pure-Python chess dependency inside the installed package;
# do NOT require `source scripts/env.sh` or `export PYTHONPATH=...`.
_vendor = _Path(__file__).resolve().parent / '_vendor'
if (_vendor / 'chess' / 'engine.py').is_file() and str(_vendor) not in _sys.path:
    _sys.path.insert(0, str(_vendor))

from .core import (
    Action, BusyError, GameBlocked, GameController, IllegalMove,
    MovePlan, Observation, PRESETS, SCHEMA_VERSION, StockfishPlayer,
    cell_to_square, describe_move, placement_from_cells, square_to_cell,
)

__all__ = [
    "Action", "BusyError", "GameBlocked", "GameController", "IllegalMove",
    "MovePlan", "Observation", "PRESETS", "SCHEMA_VERSION", "StockfishPlayer",
    "cell_to_square", "describe_move", "placement_from_cells", "square_to_cell",
]
