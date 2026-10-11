# Validation status — Integration Handover v1.0

Date: 2026-10-11.

## Already supported by earlier user test

Previous **Phase 1** self-play summary supplied by user reported 80 committed plies, no logged errors, stopped due to the 80-ply test cutoff (no chess result). This only supports the previous package's simulated-perfect-vision software path, not this revised handover version.

## Validation performed when packaging this new version

- Python source syntax/compile check: see `docs/BUILD_CHECKS.txt`.
- JSON example generation (if chess installed): not run in packaging environment.
- Unit tests (using `chess`): **NOT RUN in packaging environment** because `python-chess` was not available and network package install was blocked.
- Real Stockfish self-play with **this version**: **NOT RUN in packaging environment** because the binary is not available.
- ROS 2 Jazzy node with `rclpy`: **NOT RUN** (no ROS 2 runtime here).
- Computer Vision integration: **NOT RUN** (no camera/model attached).
- Gazebo or real robotic arms: **NOT RUN**.

This is a versioned, reviewable handover implementation, **not a validated production robotics package**. The recipient must execute unit tests and integrations and log results before declaring the system ready.

## Next acceptance checks by team

```bash
python -m unittest discover -s tests -v
python -m chess_brain_handover.selfplay --white strong --black medium --max-plies 80 --output results/demo
```

For ROS 2: `colcon build --packages-select chess_brain_handover`, run node and test sync/safety/plan/ack/fresh vision/mismatch scenarios with recorded camera messages. Then integrate Gazebo, then physical arms with independent hardware safety checks.
