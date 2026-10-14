# Architecture, two-robot design, interfaces, dependencies

## 1. Workspace / packages
Project facts used: 10 members (M1-M10); **M10 (Integration Lead) owns the ROS 2 architecture and creates the ROS 2 package structure in Week 1**; M6 owns URDF/Xacro, Gazebo+RViz, ROS 2 control, simulation; M6 delivers "robot state + joint commands" to M10. Package names below are *my recommendation* and **must be agreed with M10** (see Blockers).

```
dual_chess_ws/src/
├── dual_chess_description/   (M6)  ament_cmake  URDF/Xacro, meshes, RViz cfg, display.launch.py        [Week 1]
├── dual_chess_gazebo/        (M6)  ament_cmake  world SDF, bridge.yaml, gazebo.launch.py                [Week 1]
├── dual_chess_bringup/       (M6/M10) ament_cmake  top-level launch (simulation.launch.py)               [Week 1]
├── dual_chess_control/       (M6+M5)  ros2_control yaml, controller spawners                             [Week 3, not created]
├── dual_chess_interfaces/    (M10) ament_cmake  custom msgs/srvs/actions (only if standard ones insufficient) [M10 decides]
└── (kinematics / vision / chess-engine packages — M3 / M7 / M8 / M10 decide their own)
```
| Package | Purpose | Type | Key deps | Important files | Owner / depends | Becomes important |
|---|---|---|---|---|---|---|
| dual_chess_description | single source of truth for geometry | ament_cmake (no code) | xacro, robot_state_publisher, joint_state_publisher_gui, rviz2 | `urdf/*.xacro`, `rviz/*.rviz`, `launch/display.launch.py`, `scripts/check_urdf_structure.py` | M6; inputs M1/M2/M3/M4 | W1 (structure), W2 (real data) |
| dual_chess_gazebo | simulation world + ROS bridge | ament_cmake | ros_gz_sim, ros_gz_bridge, description pkg | `worlds/chess_world.sdf`, `config/bridge.yaml`, `launch/gazebo.launch.py` | M6 | W1, W3 (pieces) |
| dual_chess_bringup | one-command entry points | ament_cmake | gazebo+description pkgs, rviz2 | `launch/simulation.launch.py` | M6, consumed by M10 | W1, grows W3-W5 |
| dual_chess_control *(later)* | ros2_control config per arm | ament_cmake | ros2_control, ros2_controllers, gz_ros2_control | `config/robot1_controllers.yaml`... | M6 + M5 | W3, W5 (real HW) |

Why not more packages now: Week 1 is a *foundation*; fewer packages = less to redo when M10's structure lands. Why separate description / gazebo: description is reused by RViz, Gazebo, MoveIt-like planners, and real-robot bringup; Gazebo specifics must not leak into it (only the optional `sim_gazebo` plugin block).

## 2. Two-robot design (implemented)
- **One combined URDF** (`dual_chess`), root `world`, children: `board_link` (+`board_surface`,`board_a1`,`board_h8`), `robot1_base_link`, `robot2_base_link`. One `robot_state_publisher`, one TF tree.
- **Prefixes** `robot1_`/`robot2_` on every link and joint → `robot1_joint1`... no collisions.
- **Namespaces** for commands: `/robot1/jointN/cmd_pos`, `/robot2/jointN/cmd_pos`. Future ros2_control: one controller_manager namespace per arm (`/robot1`, `/robot2`) or one manager with prefixed joints — decide with M5/M10 in Week 3; joint names already unique either way.
- **Layout (PLACEHOLDER convention, needs M3/M7/M8 sign-off):** board frame origin = centre of top surface; files a→h along +X, ranks 1→8 along +Y; Robot 1 (white) at −Y facing +Y, Robot 2 (black) at +Y facing −Y.
- **Mirroring:** Proposal says "identical mechanisms with mirrored coordinate frames". I placed Robot 2 as the *same arm rotated 180° about Z* (a rigid copy, mesh reused). If M1/M3 define a true mirror (reflected geometry), only the `<origin>` / macro `reflect` handling changes — nothing else.
- Arms can be toggled: `robot1_enabled:=false`, `robot2_enabled:=false`.

## 3. Interfaces (initial, minimal)
| Interface | Direction | Week-1 realisation | Later |
|---|---|---|---|
| Joint states | sim → rest | `/joint_states` (`sensor_msgs/JointState`), names `robotN_jointM` | same; real robot publishes the same |
| TF | sim → rest | `robot_state_publisher` from URDF | + board/square frames from M3 |
| Joint commands | rest → sim | `/robotN/jointM/cmd_pos` (`std_msgs/Float64`) *stand-in* | ros2_control `JointTrajectoryController` action/topic per arm (W3) |
| Robot state | sim → M10 | joint_states + TF | status/diagnostics defined by M10 |
| FK/IK | M3 | none (M6 only *tests* it, W2-3) | IK targets `robotN_tcp_link` in `board_surface` |
| Trajectory | M3/M5 → M6 | none | `control_msgs/FollowJointTrajectory` (W3) |
| Chess manipulation | M8→M10→M6 | none | gripper interface (M2/M5), pieces in Gazebo (W3) |
Rule: no custom msg in Week 1; M10 owns the topic/service/action list — adopt theirs when published.

## 4. Dependencies from other members
None of these blocks the Week 1 deliverables (placeholders are in place). "NOW" = input expected from that member's Week 1 output, consumed by M6 in Week 2; M10 alignment is the only item to coordinate immediately.
| Member | Information needed | Why M6 needs it | When |
|---|---|---|---|
| **M10** | ROS 2 package structure, package names, topic/service/action list, namespace policy | avoid renaming my 3 packages / interfaces later; M6 delivers state+commands to M10 | **NOW (Week 1)** |
| **M1** | DOF & joint configuration; initial link dimensions + base size; joint axes | replaces placeholder 5-revolute arm and `arm_params_placeholder.xacro` | **NOW** (their Week-1 output) |
| **M1** | CAD meshes (STL/DAE, metres, mesh origin = link frame, simplified collision meshes), mass properties | visual/collision/inertia | **Week 2** (plan: "Prepare meshes for export to M6") |
| **M3** | Coordinate frames (base, joint axes/zero positions, TCP, mirrored-frame convention, board↔robot transform) | TF tree must equal their kinematic model or IK won't match sim | **NOW** (their Week-1 output), validated W2 |
| **M4** | Initial joint limits; later velocity/torque limits; workspace → robot-to-board distance | `limit` tags, base placement | **NOW** (initial limits), W2 (torque/velocity) |
| **M2** | Board square size + board thickness; piece dimensions; gripper concept/dims/TCP | board placeholder, gripper link, pieces | **NOW** (measurements), W3 (pieces) |
| **M5** | Control architecture (PID structure, stepper interface: position/velocity/step commands) | choose ros2_control interface types | **Week 2-3** |
| **M9** | Stepper torque/speed, gear ratios | effort/velocity limits, realistic sim | W2 |
| **M7** | Camera placement | optional sim camera + RViz image display | W3+ |
| **M8** | Board-state / square naming convention | consistent a1..h8 ↔ frames | W3 |
