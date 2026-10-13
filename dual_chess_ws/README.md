# Dual Robotic Arm Chess — ROS 2 Jazzy (Integration v1.2)

**Ubuntu 24.04 · ROS 2 Jazzy · Gazebo Harmonic · RViz · Stockfish · python-chess 1.11.2**

This is the **first working software integration** of the existing dual-arm simulation, Chess Brain and the Auto Game Coordinator. The robot-arm descriptions, chessboard, Gazebo world, bridge, and original simulation launch are unchanged. The arms are still **placeholder 5-DOF test models**.

> **Safety / scope:** The coordinator defaults to **passive** (`auto_play_enabled:=false`). No computer vision, robot pick-and-place executor, real safety interlocks, or full autonomous chess match is included. No mock vision/robot acknowledgement is injected into the live launch.

## 1. Folder structure

```text
dual_chess_ws/
├── README.md                       # The one project README
├── .gitignore                      # Ignores generated artifacts
├── scripts/
│   └── setup_system_dependencies.sh # Optional one-time OS setup
└── src/
    ├── dual_chess_description/     # Existing Xacro, URDF, RViz
    ├── dual_chess_gazebo/          # Existing world and ROS/Gazebo bridge
    ├── dual_chess_bringup/         # Existing main simulation.launch.py, extended
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
cd ~/dual_chess_ws
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
cd ~/dual_chess_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

**Subsequent runs**, after the workspace has been built:

```bash
cd ~/dual_chess_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

**Note:** On a truly new workspace `install/setup.bash` does **not** exist *before* the first successful `colcon build`; source it **after building**, as shown. The standard `ros2 launch` command remains the only full-system start command.

Optional development-only launch (Chess Brain + Coordinator, no Gazebo/RViz):

```bash
ros2 launch dual_chess_bringup chess_logic_only.launch.py
```

The main launch keeps its original Gazebo simulation, robot parameters, RViz and joint interfaces, and adds `/chess_brain` and `/chess_auto_coordinator` with auto-play **off** by default.

## 4. Validate after build

Open another terminal and source ROS + the overlay:

```bash
source /opt/ros/jazzy/setup.bash
source ~/dual_chess_ws/install/setup.bash
ros2 node list
ros2 topic echo /chess/state --once
ros2 topic echo /chess/auto/status --once
```

Expected nodes: `/chess_brain`, `/chess_auto_coordinator`, `/robot_state_publisher`, `/ros_gz_bridge`, `/rviz` (plus any support nodes). The initial Chess Brain FEN is `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` (white moves first). Coordinator status is expected to show `enabled:false`, `mode:passive`, `brain_state_seen:true`, `vision_seen:false`.

### Software tests (after a successful build)

```bash
cd ~/dual_chess_ws
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

## 5. ROS 2 chess interface for future integration

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

The chess controller does not commit a plan until it receives a **real, matching robot ACK** followed by **fresh, stable camera observation** matching the expected board. Stockfish White plays first. Both robot arms remain placeholders until the hardware motion stack is added.

## 6. Implementation and verification record

- Original description, world, ROS bridge, motion placeholder and top-level launch logic were preserved. Only Chess Brain dependency packaging changed in v1.2; the v1.1 simulator's launch and runtime logic were left unchanged.
- Tests verified on the developer's ROS 2 Jazzy machine for **v1.1**: 25/25 Chess Brain tests, 12/12 Coordinator tests, 12/12 Stockfish simulated plies, Gazebo/RViz and both ROS chess nodes, matching `/chess/state` and `/chess/auto/status` topics.
- **v1.2 changes require a fresh on-device check**. Static checks cannot replace an actual Gazebo/Stockfish/ROS runtime test on your machine. In particular, confirm `colcon build` (without `--symlink-install`) and then `ros2 launch ...` from a **new terminal** with no custom `PYTHONPATH`.

**Do not enable automatic chess moves on a physical setup** until the camera, robot-executor and independent safety controller are integrated and tested.
