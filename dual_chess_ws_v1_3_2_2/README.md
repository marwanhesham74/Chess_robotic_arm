# Dual Chess Workspace v1.3.2.2

This version builds on v1.3.2.1 and keeps its 8x8 black-and-white checkerboard overlay, but represents each square as its own fixed visual link so Gazebo and RViz can display alternating materials consistently. All board geometry, original CAD STL, dimensions, arm poses, launch files, and Chess Brain remain unchanged.

# Dual Chess Workspace — v1.3.2 (Original 40 cm CAD Board)

**Ubuntu 24.04 • ROS 2 Jazzy • Gazebo Harmonic • RViz • Chess Brain + Auto Coordinator**

This is **v1.3.1 with ONLY the chessboard description replaced by the supplied original `Board 1_stl.STL`**. The CAD arms, Home targets, six joint command interfaces, launch files, bridge, chess logic, and coordinator are unchanged. This is a **candidate until tested on the user's ROS 2 Jazzy machine**, not a validated hardware release.

## Quick start

This ZIP extracts into **`dual_chess_ws_v1_3_2/`**, separate from v1.3.1. Close other `dual_chess` simulations before launching it.

```bash
cd ~/dual_chess_ws_v1_3_2
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

On later runs, skip `colcon build` unless source has changed. The launch name remains **exactly** `dual_chess_bringup simulation.launch.py`.

An Ubuntu PC needs ROS 2 Jazzy, Gazebo/ros_gz, Xacro, RViz, colcon, Stockfish (`/usr/games/stockfish`), and Python build tools already installed. The Chess Brain package provisions the pinned `python-chess` on build, potentially requiring Internet on the first build. `colcon` does not install system-level `apt` dependencies. For new machines, there is an optional `scripts/setup_system_dependencies.sh` — but it is not needed if requirements are present.

## What has changed in v1.3.2

| Area | v1.3.2 |
|---|---|
| Board visual | **Unmodified original binary STL** included at `src/dual_chess_description/meshes/chess_board/Board_1_original.STL` |
| Board placement | CAD original X/Y/Z converted into ROS X/Y/Z; proper centered position and z-up |
| Outer frame | **400 × 400 mm** |
| Playing squares | **350 × 350 mm**, square pitch **43.75 mm** (NOT 50 mm), with 25 mm perimeter border |
| Height | 20.1892 mm overall; playing surface at 10 mm, raised frame up to ~20.1892 mm |
| Collision | Simplified ground slab + four raised frame rails (not a collision mesh copied from non-watertight STL) |
| Chess TF frames | `board_surface`, `board_a1`, `board_h8` preserved by name; correct positions for the physical playing squares |
| Robot base gap | Unchanged provisional **100 mm outside the 400 mm frame** (bases at ±300 mm relative to board centre) |
| Robot Home | **Unchanged** v1.3.1: both arms at `[1.570796, 1.15, 0.35]` radians after settling |
| Chess ROS nodes | Unchanged; Auto Play remains disabled by default |
| Gripper/motors | Not added; reserved for v1.3.3 and later |

**Important:** STL stores geometry, not a colour pattern. The supplied board geometry will be rendered in a single board material colour; a checkerboard colour texture/material can be added in a later visual-only update after confirming the STL view. The red/green corner markers remain to show square orientation.

**Coordinate convention:** board centre at world X=Y=0, world Z up. `board_surface` is at **world Z=0.010 m** (the playing-square surface), not the outer rim top. With +X running a→h and +Y running ranks 1→8, the centre of `a1` is `(-0.153125, -0.153125, 0.010)` and `h8` is `(0.153125, 0.153125, 0.010)` metres in the world frame. The initial board-square names remain the same, though physical dimensions have now been updated. Robot-base spacing is still provisional until mechanical installation is measured.

**CAD caveat:** input STL has multiple non-watertight components; using a simplified collision profile is intentional. Actual mass/material and motor performance are **not** verified. The chessboard remains the supplied STL; no changes were made to its bytes.

## Verify on ROS 2 Jazzy before approving v1.3.2

**Before launch** (in workspace root after build/source):

```bash
xacro src/dual_chess_description/urdf/dual_chess.urdf.xacro sim_gazebo:=true > /tmp/dual_chess_v132.urdf
check_urdf /tmp/dual_chess_v132.urdf
python3 src/dual_chess_description/scripts/check_urdf_structure.py /tmp/dual_chess_v132.urdf
python3 -m unittest discover -s src/dual_chess_description/tests -v
python3 -c "import chess_brain_handover, unittest; suite=unittest.defaultTestLoader.discover('src/chess_brain_handover/tests'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"
python3 -m unittest discover -s src/chess_auto_coordinator/tests -v
```

Then launch using the standard command above. Verify visually that both arms and the 40 cm board mesh appear in **both Gazebo and RViz**, no mesh-load or SDF graph errors appear, and Gazebo stays stable. The home controllers must reach their original target positions. Use a second terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/dual_chess_ws_v1_3_2/install/setup.bash
ros2 node list
ros2 topic echo /joint_states --once
ros2 topic echo /chess/state --once
ros2 topic echo /chess/auto/status --once
```

Expect `/chess_brain` and `/chess_auto_coordinator`; `brain_state_seen=true`, `enabled=false`, `mode=passive`, `vision_seen=false`, and white to move. The six arm joint positions should approach `[1.570796,1.15,0.35]` for each arm **after settling**, just as in v1.3.1.

**Do not approve the version yet** if any arm is missing, the board is upright/offset, Gazebo errors appear, the surface/corner orientation is wrong, or chess topics disappear. A screenshot of Gazebo/RViz plus `/joint_states` and both chess statuses is the acceptance evidence.

## Current scope and next phase

This workspace still has exactly five packages:

- `dual_chess_description` — CAD robot geometry, board CAD, frames and RViz
- `dual_chess_gazebo` — preserved world, controllers and ROS–GZ bridge
- `dual_chess_bringup` — preserved full launch including Chess Brain/Coordinator
- `chess_brain_handover` — Stockfish/python-chess, move plans and camera checks
- `chess_auto_coordinator` — passive-by-default game sequencing/safety gates

**No** actual Vision model, gripper, chess pieces, new wrist link, motion planning or physical joint controls are implemented in v1.3.2. Those will be developed only after this board-integration step passes. Chess Brain Self-Play does not prove camera or physical robot handling.
