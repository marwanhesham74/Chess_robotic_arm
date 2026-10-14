# Verification checklist and troubleshooting (everything here must be run locally on Jazzy)

> Status of each item is recorded in report §15. Already verified locally: build + launch, Gazebo spawn/joint states/commands, TF tree, RViz via `simulation.launch.py`. All items in this guide have been run locally at least once (see report §15 and Appendix A).

## Verification
### URDF / Xacro
```bash
cd ~/dual_chess_ws && source install/setup.bash
xacro $(ros2 pkg prefix --share dual_chess_description)/urdf/dual_chess.urdf.xacro > /tmp/dual_chess.urdf   # expands? (no errors)
check_urdf /tmp/dual_chess.urdf                    # urdfdom parser: prints root + tree  (sudo apt install liburdfdom-tools)
ros2 run dual_chess_description check_urdf_structure.py /tmp/dual_chess.urdf   # unique names, 1 root, connected, limits
grep -c "<link" /tmp/dual_chess.urdf; grep -c "<joint" /tmp/dual_chess.urdf     # expect 21 links, 20 joints (both arms)
xacro $(ros2 pkg prefix --share dual_chess_description)/urdf/dual_chess.urdf.xacro robot2_enabled:=false | grep -c "<link"   # expect 13
urdf_to_graphviz /tmp/dual_chess.urdf && ls dual_chess.pdf   # optional picture of the tree
```
Expected: 21 links, 20 joints (10 revolute: `robot1_joint1..5`, `robot2_joint1..5`), root `world`.

### RViz
```bash
ros2 launch dual_chess_description display.launch.py
ros2 node list          # /robot_state_publisher /joint_state_publisher_gui /rviz2
ros2 topic list         # /robot_description /joint_states /tf /tf_static
ros2 topic echo /joint_states --once
ros2 run tf2_tools view_frames      # writes frames_*.pdf: single tree rooted at world
ros2 run tf2_ros tf2_echo world robot1_tcp_link
```
Check: Fixed Frame = world (no red status); two arms (blue/orange) facing each other across the board; green h8 marker at +X+Y corner, red a1 marker at −X−Y corner; sliders move the matching joints; TF display shows `robot1_*`, `robot2_*`, `board_*`; no TF errors.

### Gazebo
```bash
ros2 launch dual_chess_gazebo gazebo.launch.py          # or: ros2 launch dual_chess_bringup simulation.launch.py
gz model --list                  # should list ground_plane and dual_chess
ros2 topic list | grep -E "clock|joint_states|robot[12]"
ros2 topic echo /joint_states --once
ros2 topic pub --once /robot1/joint1/cmd_pos std_msgs/msg/Float64 "{data: 0.6}"   # robot1 base should rotate
ros2 node list                   # /robot_state_publisher /ros_gz_bridge ...
```
Check: world opens, ground + board + two arms at the same poses as RViz, arms stay upright (not collapsing/jittering), time advances (`ros2 topic echo /clock --once`), no `[Err]` lines in the terminal.

## Troubleshooting (Symptom → Cause → Fix)
| Symptom | Cause | Fix |
|---|---|---|
| `Package 'dual_chess_description' not found` | workspace not sourced / not built | `cd ~/dual_chess_ws && colcon build --symlink-install && source install/setup.bash` (every new terminal) |
| `substitution args not supported: ... find` / xacro can't include | package not installed in `install/`, or xacro run from a different shell without sourcing | rebuild + source; use full `$(ros2 pkg prefix --share ...)` path |
| `XacroException: undefined variable` / `name 'x' is not defined` | property defined after use or in an include not loaded | order of `xacro:include`; check spelling; properties come from `arm_params_placeholder.xacro` |
| `macro 'chess_arm' ... missing parameter` | forgot `*origin` child block or a param | every `chess_arm` needs a nested `<origin .../>` |
| `check_urdf: Error: ... multiple roots / link is not connected` | missing/duplicate joint, prefix typo | run `check_urdf_structure.py`; the message names the link |
| RViz: *No transform from [robot1_base_link] to [world]* / robot white | `robot_state_publisher` not running, or Fixed Frame wrong | `ros2 node list`; set Fixed Frame = `world`; check `/robot_description` has data |
| RobotModel status: *Error subscribing: Empty topic name* / *No Description* | Description Topic not `/robot_description` | set Description Source=Topic, Topic=/robot_description (config does this) |
| Robot stuck at zero, sliders do nothing | `joint_state_publisher_gui` not started or `gui:=false` | `ros2 launch ... gui:=true`; check `ros2 topic echo /joint_states` |
| Links look wrong/inside-out after `use_meshes:=true` | mesh scale/units, mesh origin | set `arm_mesh_scale` (e.g. `0.001 0.001 0.001` for mm); ask M1 for link-frame origin |
| *Could not load mesh* / `package://` not found in RViz | mesh file missing or package not installed | file names must equal link names without prefix (`base_link.stl`); rebuild (install copies meshes) |
| Gazebo `[Err] ... attached_to name[board_link] ... does not match` / `FrameAttachedToGraph` errors | a link with no `<inertial>` fixed to `world` is removed by sdformat, orphaning frames attached to it | give that link an `<inertial>` (fixed in `board.macro.xacro`); any new world-fixed link needs one too |
| Gazebo opens but robot not spawned | spawn ran before gz was ready, or world name mismatch | `spawn_delay:=6.0`; world name must be `chess_world` in SDF, launch, bridge |
| `[ros_gz_sim]: ... Requesting list of world names` loops | gz sim not running / wrong gz version | install `ros-jazzy-ros-gz`; check `gz sim --versions` (expect Harmonic) |
| Meshes not found in Gazebo | resource path | launch appends the parent of the description share dir to `GZ_SIM_RESOURCE_PATH`; if running `gz` manually export it |
| Arms collapse or fall over | joint plugins missing | confirm `sim_gazebo:=true` expansion contains `JointPositionController` with `use_velocity_commands` |
| Uncommanded joint offset (seen: `robot1_joint5` ~0.2 rad with the PID version) or jitter | force-mode PID vs tiny placeholder inertia | current build uses velocity-command mode (no PID); if it returns, check masses/inertia in `arm_params_placeholder.xacro` and keep `max_step_size` 0.001 |
| `/joint_states` empty in sim | bridge not running or model/world name changed | `ros2 node list | grep bridge`; `gz topic -l | grep joint_state`; names in `config/bridge.yaml` |
| Commands ignored | topic mismatch | `gz topic -l | grep cmd_pos`; message type `std_msgs/Float64` |
| TF warnings *Moved backwards in time* | mixing sim time and wall time (RViz without `use_sim_time`) | start RViz via `simulation.launch.py` (sets sim time) |
| Duplicate names / two arms overlap | both macros got same prefix/origin | prefixes `robot1_`/`robot2_`, distinct `<origin>` in `dual_chess.urdf.xacro` |
| Later: *controller_manager not available* / controller fails | ros2_control not set up yet (Week 3) or both gz plugins AND ros2_control active | remove hold plugins when adding `gz_ros2_control` |
