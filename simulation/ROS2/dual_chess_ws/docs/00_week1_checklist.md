# M6 Week 1 — Requirements checklist (source: Week1_Tasks.pdf, page 8; context: Team Structure + Proposal)

Deadline: **Thursday 11:59 PM**. If blocked, report immediately (do not wait for Thursday).
Quality bar (last page of Week 1 PDF): **Research → Understanding → Initial Decision → Initial Work → Clear Next Step**,
readable enough that another member can continue next week.

## Required this week  (official)
| # | Requirement | Where it is in this repo | Status |
|---|---|---|---|
| 1 | **Submit: URDF/Xacro structure** | `dual_chess_description/urdf/` | Implemented; Verified (sandbox + local: `check_urdf`, launch, TF, RViz; placeholder model) |
| 2 | **Submit: Initial Gazebo environment** | `dual_chess_gazebo/worlds/chess_world.sdf`, `launch/gazebo.launch.py` | Implemented; Verified locally (placeholder model): Gazebo GUI, `gz model --list`, joint states, commands |
| 3 | **Submit: Initial RViz setup** | `dual_chess_description/rviz/dual_chess.rviz`, `launch/display.launch.py` | Implemented; Verified locally via `display.launch.py` (sliders) and `simulation.launch.py` |
| 4 | Report section **Research**: URDF/Xacro, Gazebo, RViz | `docs/01_research.md`, report §4-7 | Draft ready |
| 5 | Report section **ROS 2 Structure**: package/file structure | `docs/02_architecture.md`, report §8 | Draft ready |
| 6 | Report section **URDF/Xacro: initial structure** | report §9 | Draft ready |
| 7 | Report section **Gazebo: initial environment** | report §10 | Draft ready |
| 8 | Report section **RViz: initial setup** | report §11 | Draft ready |
| 9 | Report section **Dependencies: what is needed from M1/M3** | `docs/02_architecture.md` §Dependencies, report §12 | Draft ready |
| 10 | Report section **Blockers** | report §13 | Draft ready — *you must confirm/extend with real blockers* |
| 11 | Report section **References** | report §17 | Draft ready |

Team-structure Week 1 line for M6: "Prepare URDF/Xacro structure" and "Prepare Gazebo environment and RViz". End-of-week milestone for the whole team includes a **ROS skeleton**.

## Future work (do NOT build now; kept as extension points only)
| Week | M6 item (Team Structure PDF) |
|---|---|
| 2 | Convert CAD to URDF/Xacro; add real links, joints, mass/inertia, joint limits, collision models; run in Gazebo + RViz; build Robot 1 and Robot 2 |
| 3 | Connect the controller (ROS 2 control); test arm motion; add chessboard and chess pieces in Gazebo |
| 4 | Complete trajectory tests for both robots in simulation |
| 5 | Support the real-robot interface (ROS 2 control) |

## Things the repo does that go slightly beyond the official Week 1 ask (delete freely)
- Gazebo `JointPositionController` plugins (velocity-command mode) + `/robotN/jointM/cmd_pos` bridge (so you can *see* the arms hold/move). Temporary simulation-level stand-in, NOT the final control architecture; replaced by ros2_control in Week 3. Remove `urdf/arm/arm.gazebo.xacro` hold plugins when ros2_control arrives.
- `use_meshes` switch (cheap; makes Week 2 CAD swap a one-argument change).

## Not in the PDFs (so they are placeholders, never facts)
DOF, joint types/axes, link lengths, joint limits, torque/velocity limits, masses/inertias, gripper geometry, TCP offset, board/square size, board-to-robot distance, mirrored-frame convention, the topic/service/action names (M10), controller type (M5).
