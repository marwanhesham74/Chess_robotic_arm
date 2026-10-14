# M6 Week 1 — Research (URDF, Xacro, Gazebo, RViz) for the dual-arm chess robot

> Proposal pipeline this research serves: **CAD → Mesh → URDF/Xacro → ROS 2 → Gazebo → RViz** (Proposal §12).
> Items marked *(project)* come from the PDFs; *(recommendation)* are my engineering choices.

## A. URDF
**What it is.** Unified Robot Description Format: an XML tree of `<link>` and `<joint>` elements describing a robot's kinematic tree. ROS 2 tools read it from the `robot_description` parameter.

**Links** = rigid bodies. Each can have `<visual>` (what you see), `<collision>` (what physics uses; keep simple), `<inertial>` (mass, centre of mass `origin`, 3x3 inertia).
**Joints** connect a *parent* link to a *child* link and define the child frame's pose (`<origin>`), the axis, limits, dynamics.
Types: `fixed`, `revolute` (limited), `continuous` (unlimited), `prismatic`, `floating`, `planar`.
**Rules:** it must be a *tree* — exactly one root, one parent per link, no loops. Link/joint names unique. Units SI (m, kg, rad, s) per REP 103.
**Frames:** each link has its own frame at its joint origin; the child frame is placed by the joint `<origin>`, then rotated about `<axis>` by the joint value. TF is derived from this (REP 105 naming: `base_link`, `world`...).
**Limits:** `lower/upper` (rad), `velocity` (rad/s), `effort` (N·m) are mandatory for `revolute`. Simulation and planners enforce them.
**Mass/inertia:** Gazebo needs positive mass and a physically valid inertia tensor on every moving link, or the arm explodes/collapses. Primitive formulas (box/cylinder) are used as placeholders; CAD mass properties replace them (M1, Week 2).
**Why URDF for us:** it is the single source for RViz (RobotModel), `robot_state_publisher` (TF), Gazebo (spawned as SDF), ros2_control (joint list) and later IK/planning (M3/M10).

**In our project:** two identical arms (Proposal §3, §6: "identical mechanisms with mirrored coordinate frames") on opposite sides of one board. URDF will hold per arm: links, joints, limits, visual, collision, mass, inertia, frames (Proposal §12 list). *DOF/dims are not specified yet → placeholder 5-revolute arm.*

## B. Xacro
**What:** XML macro language that expands to URDF (`xacro file.xacro > file.urdf`; launch files call it on the fly).
**Why vs raw URDF:** a raw dual-arm URDF would be ~2x the same XML; any M1 change would need editing twice. Xacro gives:
- `<xacro:property>` constants (all placeholders live in `arm_params_placeholder.xacro`), with `${...}` math (`${pi/2}`, inertia formulas);
- `<xacro:macro>` reusable blocks with parameters and *block parameters* (`*origin`);
- `<xacro:arg>` launch-time switches (`robot2_enabled:=false`, `use_meshes:=true`, `sim_gazebo:=true`);
- `<xacro:if>/<xacro:unless>` conditionals; `<xacro:include>` split across files; `$(find pkg)` paths.
**Prefixes:** the macro takes `prefix` ("robot1_"), and *every* link/joint name is `${prefix}name`. Two instantiations → no TF/joint name clashes. Materials are global in URDF, so they are defined once (not inside the macro).
**Our architecture** (`urdf/`):
```
dual_chess.urdf.xacro        top level: args, world link, board, robot1, robot2, gazebo-only parts
common/materials.xacro       global materials
common/inertial_macros.xacro box/cylinder inertia helpers
board/board_params_placeholder.xacro   board+layout placeholders
board/board.macro.xacro      chess_board macro (board_link, board_surface, a1/h8 frames)
arm/arm_params_placeholder.xacro       ALL arm placeholders (edit here)
arm/arm.macro.xacro          arm_link, arm_joint, chess_arm macros
arm/arm.gazebo.xacro         Gazebo hold-controller plugins (Week-1 stand-in)
```

## C. Gazebo
Use **Gazebo Harmonic** (gz-sim 8), the officially paired release for ROS 2 Jazzy, via `ros_gz` (*recommendation; check installed version locally*).
Provides: physics (DART default; gravity, step size), collision detection, rigid-body joints, sensors (camera, lidar, IMU...), plugins/systems (joint controllers, state publishers), worlds in SDF, a GUI, and ROS 2 integration through `ros_gz_sim` (launch/spawn) and `ros_gz_bridge` (topics).
**Spawning:** `ros_gz_sim create -topic robot_description -name dual_chess` converts the URDF to SDF and inserts it. A URDF link called `world` joined by a fixed joint is treated as fixed to the world.
**Controllers:** (a) gz system plugins (what Week 1 uses for hold/commands), (b) `gz_ros2_control` + ros2_control (Week 3, Team Plan "Connect the controller (ROS 2 control)").
**What Gazebo will do for us (Proposal §13):** robot physics, joint movement, collision detection, motion testing, chess-piece manipulation, two-robot interaction.
| Capability | Week 1 | Later |
|---|---|---|
| World, ground, light, physics | **Yes** | |
| Board (static, from URDF), both robots spawned at placeholder poses | **Yes** | real dims W2 |
| Joint hold/command stand-in + `/joint_states` | Yes (small) | ros2_control W3 |
| Real meshes/inertia/collision tuning | | W2 |
| Chess pieces, grippers grasping, friction tuning | | W3-4 |
| Camera sensor (M7) | | when M7 fixes placement |
| Two-arm coordination/collision tests | | W4 |

## D. RViz (RViz 2)
3D visualizer; it *renders* ROS data, it does not simulate.
- **Fixed Frame:** the global reference frame all displays are transformed into. Ours: `world`.
- **TF display:** shows every frame (axes/arrows/names) from `/tf` + `/tf_static`; the main tool to debug frame conventions (M3 will compare their frames with ours).
- **RobotModel:** draws `/robot_description` posed by TF; can show collision geometry (second display, disabled by default).
- **Joint visualization:** RViz has no joint widget; joints are driven by `/joint_states` (`joint_state_publisher_gui` sliders in Week 1; Gazebo in sim).
- **Grid, Axes, Markers, Sensor displays:** LaserScan/PointCloud/Image for sensors (Proposal §13 "sensor visualization" — only relevant after M7 adds a camera).
- **Useful for:** TF errors, wrong joint axis/limit, mirrored-frame bugs, checking IK targets later.
Initial config: Grid, RobotModel (visual), RobotModel (collision, off), TF; Fixed Frame `world`; Orbit camera looking at board.

## E. Mapping to ROS 2 pieces
`robot_state_publisher` (URDF + joint states → TF), `joint_state_publisher(_gui)` (fake joint states, RViz-only), `xacro`, `rviz2`, `ros_gz_sim`, `ros_gz_bridge`, `tf2_tools` (`view_frames`).
