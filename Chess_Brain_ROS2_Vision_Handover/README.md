# Dual Robotic Arm Chess Brain — ROS 2 / Vision handover v1.0

**Purpose:** integrate ready-to-use chess rules and UCI Stockfish move selection into a dual robotic arm chess architecture. **No external chess game dataset, training, or chess-playing model is required.**

Includes:

- Single authoritative `python-chess` board, game-over handling, legal move validation, move history.
- Stockfish UCI engine adapter with independent White/Black skill presets.
- `MovePlan` with deterministic logical action descriptions (`remove`, `move`, `promote`), UCI/SAN, before/expected FEN, chess square and 0-based row/column coordinates.
- Verification: initial stable/calibrated camera sync; robots-ready safety gate in ROS; plan-ID-specific robot ack; post-ack fresh vision; no logical commit until all requirements pass.
- Separate ROS 2 Jazzy `ament_python` JSON bridge via standard ROS `String`/`Bool` messages.
- Fake-vision/fake-robot selfplay for software testing and explicit unit tests.

**Start here:** `README_AR.md` for Arabic explanation and installation; `docs/INTEGRATION_CONTRACT.md` for team interface specifications; `docs/VALIDATION_STATUS.md` for current testing limitations.

## Install (Python only)

```bash
sudo apt update && sudo apt install stockfish python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
python -m chess_brain_handover.selfplay --white strong --black medium --max-plies 80 --output results/demo
```

## ROS 2

This directory itself is an `ament_python` package. Place it in an existing Jazzy workspace under `src/chess_brain_handover`, build with `colcon build --symlink-install`, and run:

```bash
ros2 run chess_brain_handover chess_brain_node --ros-args -p engine_path:=/usr/games/stockfish
```

The active ROS Python environment needs both `rclpy` and the PyPI distribution `chess` (imported as `chess`), plus `std_msgs`. See `README_AR.md` for environment guidance.

**Safety limitations:** This package does not control joint trajectories, verify grasp force, enforce workspace collision constraints, or substitute for hardware interlocks. ROS Strings are the handover prototype; production deployments should use typed ROS 2 messages, ROS Actions, timeout monitors, and a protected safety controller. Stockfish itself is licensed GPLv3; redistributing an engine binary requires respecting its license.
