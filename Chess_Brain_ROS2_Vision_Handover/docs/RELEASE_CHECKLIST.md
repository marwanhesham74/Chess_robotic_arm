# Acceptance checklist — handover signatures

This v1.0 source handover is NOT production acceptance. Fill results after real tests.

| Check | Owner | Status |
|---|---|---|
| Python `chess` installs on Ubuntu 24.04 (Python 3.12) | Chess maintainer | NOT RUN HERE |
| `python -m unittest discover -s tests -v` passes | Chess maintainer | NOT RUN HERE |
| Stockfish vs Stockfish example saves valid `moves.csv` and `summary.json` | Chess maintainer | NOT RUN FOR v1.0 HERE |
| ROS 2 Jazzy colcon build + launch succeeds | ROS 2 team | NOT RUN HERE |
| 64-cell board maps a8=(0,0), e4=(4,4), h1=(7,7) | Vision team | WAITING FOR AGREEMENT |
| Vision emits per-cell confidence and synchronized Unix timestamps | Vision team | NOT CONNECTED |
| Illegal/unstable/stale camera messages rejected | Joint bench test | NOT CONNECTED |
| Duplicate `plan_id` cannot execute twice | Motion executor team | NOT CONNECTED |
| Robot ack only after full completion and safe park | Robotics team | NOT CONNECTED |
| Capture, en passant, castling, promotion gripper sequences | Robotics team | NOT CONNECTED |
| Two arms' workspace/collision limits/physical E-stop validated | Safety team | NOT CONNECTED |
| Simulated Gazebo complete game + logging | Integration team | NOT CONNECTED |
| Physical chessboard dry-run with speed limits and stop/recovery | Integration team | NOT CONNECTED |

**Do not mark the complete dual-arm robot integration safe until the hardware safety checks pass.**
