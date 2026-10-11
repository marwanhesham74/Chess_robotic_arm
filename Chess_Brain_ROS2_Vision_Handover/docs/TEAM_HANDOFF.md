# Who gets what?

## Team lead

Send the ZIP unchanged, together with this summary:

- Chess engine: Stockfish through UCI, via python-chess. No training dataset used.
- Core API: `GameController` in `chess_brain_handover/core.py`.
- Vision input: 8×8 cells, mandatory calibrated orientation `a8_top_left`, FEN symbols, calibrated stable frame and confidence + timestamp. Canonical format in `INTEGRATION_CONTRACT.md`.
- Robotics output: `/chess/move_plan` JSON with `plan_id`, `from_sq`, `to_sq`, `from_cell`, `to_cell`, ordered actions. Robotics computes XYZ, IK/trajectory and collision safety.
- Verification: independent robot ack + fresh vision required. No automatic resync on mismatch.
- ROS node: `ros2 run chess_brain_handover chess_brain_node`.
- Delivery status: coding/packaging completed, runtime acceptance by recipient pending (documented in VALIDATION_STATUS).

## Computer Vision team

Only read section A/B/G/H in integration contract initially.
Implement robust calibrated 64-cell board observation with per-cell class+confidence and timestamp, not only row/col occupancy. The camera should observe a parked-robot board with hands out of view.

## ROS/Robotics team

Read sections C through H. Implement ROS motion executor that treats a `plan_id` as single-use, converts each logical square to calibrated arm XYZ, handles capture bins and spare promotion pieces, reports ack after arm parked, and publishes safety readiness through an independent safe coordinator.

## Game logic maintainer

Run unit tests; run real Stockfish self-play; review `chess_brain_handover/core.py`; align interfaces with teams. Do NOT use fake vision/ack from selfplay in hardware code.
