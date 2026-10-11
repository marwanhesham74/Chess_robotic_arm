# ROS 2 Jazzy quickstart (handover team)

**This is a bridge sample, not safety or motion software.** The package contains the chess node and a launch file; it intentionally does not start camera or arms.

## Install

Read `README_AR.md` for Python/ROS environment steps and `docs/INTEGRATION_CONTRACT.md` for schema.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/chess_ws
colcon build --symlink-install --packages-select chess_brain_handover
source install/setup.bash
ros2 launch chess_brain_handover chess_brain.launch.py engine_path:=/usr/games/stockfish
```

## Topics to connect

| Direction | Topic | ROS type | Publisher/consumer |
|--|--|--|--|
| IN | `/chess/vision/board` | `std_msgs/msg/String` JSON | Vision team (64 cells required) |
| IN | `/chess/robot_ack` | `std_msgs/msg/String` JSON | Robot motion executor |
| IN | `/chess/safety_ready` | `std_msgs/msg/Bool` | Independent safety coordinator |
| IN | `/chess/command` | `std_msgs/msg/String` JSON | Authorized operator/coordinator |
| OUT | `/chess/move_plan` | `std_msgs/msg/String` JSON | Chess Brain -> robot executor |
| OUT | `/chess/state` | `std_msgs/msg/String` JSON | Chess Brain -> UI/coordinator |
| OUT | `/chess/events` | `std_msgs/msg/String` JSON | Chess Brain -> diagnostics |

Observe:

```bash
ros2 topic echo /chess/events
ros2 topic echo /chess/move_plan
ros2 topic echo /chess/state
```

**Safe sequence:** Vision publishes accurate initial 64-cell board -> operator sends `{ "action": "sync" }` -> coordinator sends safety_ready true -> operator sends `{ "action": "next" }` -> executor receives unique `plan_id` and executes -> executor sends success ack with the same ID only after the arm is parked and gripper has released -> camera publishes fresh post-ack board -> Brain commits if it matches.

Command examples (after `sync`, for a connected integration environment):

```bash
ros2 topic pub --once /chess/command std_msgs/msg/String '{data: "{\"action\":\"state\"}"}'
ros2 topic pub --once /chess/command std_msgs/msg/String '{data: "{\"action\":\"sync\"}"}'
ros2 topic pub --once /chess/command std_msgs/msg/String '{data: "{\"action\":\"next\"}"}'
```

Do NOT publish a fake `safety_ready=true` or a fabricated success ACK on the physical rig. Use them only in an isolated simulation with hardware disconnected.

## What to configure

- Robot team maps each plan action to a geometrically verified pose and ensures safe pick/place (collision, grasp, bins, spare pieces).
- Vision team calibrates orientation and time synchronization and publishes all 64 cells with per-cell confidence.
- Control team implements watchdogs for ROS message loss, plan acknowledgement timeout, emergency stops, and an operator recovery procedure.
- Under ROS, automatic plan generation is **not** activated; `next` must be requested explicitly after the last commit and a new safety-ready signal.
