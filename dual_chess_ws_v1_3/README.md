# Dual Robotic Arm Chess — ROS 2 Jazzy (CAD Integration v1.3 Candidate)

**Ubuntu 24.04 · ROS 2 Jazzy · Gazebo Harmonic · RViz · Stockfish · python-chess 1.11.2**

This version builds on the **v1.2 software integration** of chess logic, passive coordinator and Gazebo/RViz. The chess logic and passive coordinator are unchanged from the successfully tested v1.2. **Each arm is now the supplied SolidWorks CAD geometry** (STL), with three modeled joints: `base_yaw_joint`, `joint1`, and `joint2`. The board remains a PLACEHOLDER until board CAD arrives; the gripper is not modeled yet. The base-yaw axis is an **explicit design assumption**, NOT verified from the original exported SolidWorks joint tree. This v1.3 package is a **test candidate until checked on real ROS 2 Jazzy/Gazebo**, not a certified physical robot model.

> **Safety / scope:** The coordinator defaults to **passive** (`auto_play_enabled:=false`). No computer vision, robot pick-and-place executor, real safety interlocks, or full autonomous chess match is included. No mock vision/robot acknowledgement is injected into the live launch.

## 1. Folder structure

```text
dual_chess_ws_v1_3/
├── README.md                       # The one project README
├── .gitignore                      # Ignores generated artifacts
├── scripts/
│   └── setup_system_dependencies.sh # Optional one-time OS setup
└── src/
    ├── dual_chess_description/     # CAD Xacro (STL, 3 joints/arm), board placeholder, RViz
    ├── dual_chess_gazebo/          # Preserved world, bridge updated to 6 CAD joint commands
    ├── dual_chess_bringup/         # Original simulation.launch.py with Chess nodes
    ├── chess_brain_handover/       # python-chess, Stockfish UCI, ROS chess node
    └── chess_auto_coordinator/    # Passive-by-default turn/safety coordinator
```

`build/`, `install/` and `log/` are created by `colcon build`; **do not upload them**. The build may also create `src/chess_brain_handover/chess_brain_handover/_vendor/`; this is generated and ignored by Git.

## 2. Requirements (once per new PC)

- Ubuntu 24.04 with **ROS 2 Jazzy** installed and `source /opt/ros/jazzy/setup.bash` working.
- ROS 2 Gazebo integration (`ros_gz_sim`/`ros_gz_bridge`), `xacro`, `robot_state_publisher`, `rviz2`, and `colcon`.
- `/usr/games/stockfish` from Ubuntu `stockfish`, and `python3-pip` for the first build when `chess` is not locally available.

**Important limitation:** `colcon build` builds ROS packages; it does **not** automatically install system-level `apt` dependencies, Stockfish, ROS 2 or Gazebo. You must install those **once per machine** before your first build. Official Jazzy installation: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

For a new machine with ROS Jazzy already installed, optionally run this **one-time** setup (it asks before using `sudo apt`):

```bash
cd ~/dual_chess_ws_v1_3
bash scripts/setup_system_dependencies.sh
```

It checks for broken `dpkg` state and refuses to run if the package manager is already broken, instead of risking the NVIDIA/kernel package issues. If dependencies are already installed, you do **not** need this script.

### How python-chess is handled automatically

`chess_brain_handover/setup.py` provisions the **pinned `chess==1.11.2`** into that ROS package during a regular `colcon build` **and** a `colcon build --symlink-install`:

1. Reuses the package-local copy on subsequent builds.
2. Reuses a local matching copy, including `~/.venvs/chess_ros2` from v1.1, if present (works offline).
3. Otherwise downloads the pinned public PyPI package **on the first build only** (requires Internet access and `python3-pip`).

`chess_brain_handover/__init__.py` loads this isolated copy from inside its own ROS package. **No virtual-environment activation, `env.sh`, `launch.sh`, `PYTHONPATH`, `pip --break-system-packages`, or manual `pip install chess` is needed at runtime.** `colcon` does not alter the system Python installation.

If the first-build download fails due to no network, the build stops with an actionable error; it must not silently produce a broken executable. Offline first builds need a matching local copy already available.

**Third-party licensing:** python-chess is GPL-3.0-or-later (https://github.com/niklasf/python-chess); Stockfish is GPL-3.0-or-later (https://stockfishchess.org). This project does not include an executable Stockfish binary. Follow their license terms when redistributing third-party files.

## 3. Build and launch — standard ROS commands

**Fresh clone/extracted ZIP (first build):**

```bash
cd ~/dual_chess_ws_v1_3
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

**Subsequent runs**, after the workspace has been built:

```bash
cd ~/dual_chess_ws_v1_3
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

**Note:** On a truly new workspace `install/setup.bash` does **not** exist *before* the first successful `colcon build`; source it **after building**, as shown. The standard `ros2 launch` command remains the only full-system start command.

Optional development-only launch (Chess Brain + Coordinator, no Gazebo/RViz):

```bash
ros2 launch dual_chess_bringup chess_logic_only.launch.py
```

The main launch still starts Gazebo, RViz, Chess Brain, and passive Auto Coordinator. It now publishes **CAD geometry with the unchanged canonical Xacro filename** `urdf/dual_chess.urdf.xacro`; the deprecated `use_meshes` argument is accepted but ignored because CAD meshes are always used. The robot commands in the bridge are **three joints per arm**. Auto-play remains **OFF** by default.

## 4. CAD-specific changes, assumptions and motion checks

**CAD source:** user-supplied SolidWorks export `Assem4.SLDASM.urdf`, three nonduplicate STL meshes (`link0`, `link1`, `link2`), and corrected Xacro candidate. The nonduplicate CAD base geometry is rendered once on the `base_yaw_link`. Frame-only aliases `base_link` / `link0` and their fixed transforms preserve the exported geometry positioning. `link1` and `link2` retain exported joint origins/axes and measured/exported inertial tensors. Reference STL `base_link.STL` overlapped `link0.STL` and was omitted (do not sum the two base masses).

**ROS joint command topics (only these six):**

```text
/robot1/base_yaw_joint/cmd_pos    /robot2/base_yaw_joint/cmd_pos
/robot1/joint1/cmd_pos            /robot2/joint1/cmd_pos
/robot1/joint2/cmd_pos            /robot2/joint2/cmd_pos
```

The **simulation-only** Gazebo position controller's configured maximum velocity is 0.4 rad/s. This is NOT an actual motor rating, PID design, or hardware safety guarantee. All three joints remain **provisionally `continuous`**, because mechanical travel stops, gearbox, torque and max speed have not yet been specified. The modeled base-yaw motor location is a **design intention** at each base frame's local Z axis. The base housing is represented as the moving yaw link in this candidate; the CAD team must confirm whether the housing itself rotates or a shaft rotates inside a stationary housing.

**Temporary elements:** chessboard box and arm-base spacing from `board_params_placeholder.xacro`, simplified primitive collision geometries, absent gripper/TCP, no chess pieces, no IK/Motion Planner, no motor control. The three CAD STL meshes are always enabled in Gazebo and RViz.

**Validate the robot before touching the v1.2 backup:**

```bash
# Build (after the system requirements above are available):
cd ~/dual_chess_ws_v1_3_v1_3
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash

# Native Xacro and URDF validation:
xacro src/dual_chess_description/urdf/dual_chess.urdf.xacro sim_gazebo:=false > /tmp/dual_chess_v13.urdf
check_urdf /tmp/dual_chess_v13.urdf
python3 src/dual_chess_description/scripts/check_urdf_structure.py /tmp/dual_chess_v13.urdf
xacro src/dual_chess_description/urdf/dual_chess.urdf.xacro sim_gazebo:=true > /tmp/dual_chess_v13_sim.urdf
check_urdf /tmp/dual_chess_v13_sim.urdf

# Normal full launch remains exactly the same:
ros2 launch dual_chess_bringup simulation.launch.py
```

In a second terminal (with both ROS setups sourced), inspect `ros2 node list`, `/joint_states`, `/chess/state` and `/chess/auto/status`. Gazebo spawn must say `Entity creation successful`. In Gazebo, **manually test one joint at a time with the other arm parked and verify positive/negative rotation**, then inspect TF, mesh placement, ground penetration and any self-collision. Example simulation-only command (small angle, radians):

```bash
ros2 topic pub --once /robot1/joint1/cmd_pos std_msgs/msg/Float64 "{data: 0.1}"
```

**Integration acceptance requires:** 6 real joint-state names, six matching bridge command topics, both CAD arms visible in RViz/Gazebo, 3 joints/arm moving in correct directions, no mesh-loading errors, preserved Chess Brain/Coordinator messages. **Native Gazebo and hardware tests were not available in the authoring environment**; do not merge this candidate into an already working v1.2 before this acceptance run.

---

## 5. Validate after build

Open another terminal and source ROS + the overlay:

```bash
source /opt/ros/jazzy/setup.bash
source ~/dual_chess_ws_v1_3/install/setup.bash
ros2 node list
ros2 topic echo /chess/state --once
ros2 topic echo /chess/auto/status --once
```

Expected nodes: `/chess_brain`, `/chess_auto_coordinator`, `/robot_state_publisher`, `/ros_gz_bridge`, `/rviz` (plus any support nodes). The initial Chess Brain FEN is `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` (white moves first). Coordinator status is expected to show `enabled:false`, `mode:passive`, `brain_state_seen:true`, `vision_seen:false`.

### Software tests (after a successful build)

```bash
cd ~/dual_chess_ws_v1_3
python3 -m unittest discover -s src/chess_brain_handover/tests -v
python3 -m unittest discover -s src/chess_auto_coordinator/tests -v
python3 -m chess_brain_handover.selfplay --white strong --black medium \
  --max-plies 12 --output /tmp/dual_chess_selfplay_test
cat /tmp/dual_chess_selfplay_test/summary.json
```

Self-play is **simulated perfect vision and execution**. It does not test any camera, joint movement, gripper, or hardware safety. The acceptance target is 12 plies and 0 errors, not a completed chess match.

### Other existing launches

```bash
ros2 launch dual_chess_description display.launch.py   # RViz-only display
ros2 launch dual_chess_gazebo gazebo.launch.py        # Gazebo only
```

## 6. ROS 2 chess interface for future integration

| Topic | Message | Owner / purpose |
|---|---|---|
| `/chess/vision/board` | `std_msgs/String` JSON | Future overhead **single-camera** perception publishes 64 cells |
| `/chess/state` | `std_msgs/String` JSON | Chess Brain authoritative board and turn |
| `/chess/command` | `std_msgs/String` JSON | `sync`, `next`, `manual`, `reset`, `state` |
| `/chess/move_plan` | `std_msgs/String` JSON | Piece movement plan for future robot executor |
| `/chess/robot_ack` | `std_msgs/String` JSON | Real execution acknowledgement |
| `/chess/safety_ready` | `std_msgs/Bool` | External real safety/robot-ready signal |
| `/chess/events` | `std_msgs/String` JSON | State/event log |
| `/chess/auto/status` | `std_msgs/String` JSON | Coordinator state |

Vision sends one record for **each of the 64 squares**, with `row=0` meaning rank 8 and `col=0` meaning file a (`a8` at top left), `piece` in `PNBRQKpnbrqk` or `.` empty, calibrated and stable flags, confidences and a real Unix capture timestamp. See `src/chess_brain_handover/reference/vision_64cells_TEMPLATE.json` for the example and `reference/board_coordinates_64.csv` for mapping.

The chess controller does not commit a plan until it receives a **real, matching robot ACK** followed by **fresh, stable camera observation** matching the expected board. Stockfish White plays first. The arm meshes now reflect the supplied CAD, but the Gazebo controller is a simulation stand-in until a verified hardware motion stack is integrated.

## 7. Implementation and verification record

- **Unchanged from v1.2:** all Chess Brain and Auto Coordinator source/config/tests, Bringup source, original Gazebo world, RViz configuration, and system-dependency setup helper.
- **Changed for CAD:** canonical arm/top-level Xacros, three STL meshes, description metadata, Gazebo bridge six joint-command mappings. Only docstrings in Gazebo/display Launch changed; **launch behavior and entrypoint remain the same**.
- v1.2 was verified on the user's ROS 2 Jazzy machine: 25/25 Chess Brain unit tests, 12/12 Coordinator unit tests, 12/12 Stockfish simulated plies, Gazebo/RViz startup, chess nodes and state/status messages. These are **v1.2 results**, not proof of v1.3's CAD motion.
- Portable v1.3 tests are in `src/dual_chess_description/tests/test_cad_integration.py`, runnable with `python3 -m unittest discover -s src/dual_chess_description/tests -v`. They check file structure, XML syntax, three links' masses/inertias, canonical Xacro entrypoint and controller/bridge mapping. **Real ROS 2, native Xacro/check_urdf and Gazebo motion checks remain outstanding until run on a Jazzy PC.**

Do not enable automatic chess moves or hardware actuation until the camera, motion executor and independent safety supervisor are fully integrated and tested. Retain v1.2 unchanged until the CAD designer signs off the yaw-axis implementation and all native ROS acceptance checks pass.
