# Dual Chess Workspace v1.3.3.4 — Gripper Steady-State Tuning Candidate

**Based directly on tested v1.3.3.3, not on v1.4.** User runtime logs show that BOTH
Robot 1 and Robot 2 can travel forward / reverse but stop approximately
**+1.206 mm above their commanded prismatic positions** at 0, 10, 20, 40 mm.
This revision modifies ONLY the temporary gripper Gazebo PID: `i_gain=3.0`,
`i_max=0.05`, `i_min=-0.05`. It retains `p_gain=10`, `d_gain=0.7`,
effort limits `+/-1.0` and collision modifications from v1.3.3.3. A low bounded
integral should reduce a persistent steady-state bias, but this is a hypothesis
until verified on the user's ROS 2 Jazzy / Gazebo machine.

**No other package implementation is changed.** The original arm meshes,
CAD joint transforms, wrist shape, checkerboard, Home pose, brain,
auto coordinator, Gazebo bridge, and simulation.launch.py remain unchanged.
This is NOT calibrated for physical gripper hardware.

## Main launch (unchanged)

Stop old Gazebo instances, extract archive to your Home and run:

```bash
cd ~/dual_chess_ws_v1_3_3_4
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

## Gripper precision acceptance test

In a second terminal, first source `/opt/ros/jazzy/setup.bash` and
`~/dual_chess_ws_v1_3_3_4/install/setup.bash`.
For **each** of `robot1`, `robot2`, command positions
`0.00`, `0.01`, `0.02`, `0.04`, `0.00` metres, with a ~7 second pause after each command
(allow time for integral correction), then inspect `/joint_states` by joint name.

```bash
for robot in robot1 robot2; do
  for pos in 0.00 0.01 0.02 0.04 0.00; do
    echo "ROBOT=$robot TARGET=${pos}m"
    timeout 8s ros2 topic pub -r 5 "/${robot}/gripper_finger_joint/cmd_pos"       std_msgs/msg/Float64 "{data: $pos}" 
    ros2 topic echo /joint_states --once
  done
done
```

**Candidate pass criterion (simulation only):** absolute steady-state error
at each target under **0.0005 m (0.5 mm)**, repeatable for both grippers without
sticking at 0.045 m, with no major oscillation or inter-arm collision.
If this threshold is not met, do NOT certify this candidate: compare the actual
positions / time response and tune again. Verify `/chess/state`,
`/chess/auto/status`, Gazebo and RViz remain normal.
Warnings `A message was lost!!!` in `ros2 topic echo` concern feedback
subscriber dropouts, not proof of an actuator fault.

---

# Dual Chess Workspace v1.3.3.3 — Gripper Return Control Candidate

**Based on v1.3.3.2. Do not overwrite the verified earlier workspace.**
This patch is intended to correct the temporary prismatic gripper getting stuck
at its 0.045 m upper travel stop when commanded to 0.02 m and then 0.0 m.
The failure was reproduced via ROS 2 *and* `gz topic` on the user's Jazzy machine.

## Minimal changes

- `arm_cad.gazebo.xacro`: ONLY the two gripper controllers change to
  effort/PID position mode with no integral windup and force-limited provisional
  gains. Four previously tested arm joints per robot keep the existing position
  control and Home values.
- `arm_cad.macro.xacro`: adjust **collision boxes only** at the finger tips to
  remove intersection with the palm approximation during the slide. No visual
  meshes, links, joint origins, finger travel limits or CAD geometry change.
- Add `test_gripper_controller_fix.py` portable static regression test.

This is a **simulation workaround**, not a physical gripper motor design. PID
and effort limits are not calibrated. The Gazebo/ROS issue is not proven fixed
until the following test actually passes on your machine.

## Run (same launch command)

```bash
cd ~/dual_chess_ws_v1_3_3_3
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

Close ALL old Gazebo/ROS launch instances first and open a separate shell sourced
from the **v1.3.3.3** workspace (not the old v1.3.3.2 install).

## Required gripper acceptance test

After a **fresh launch**, without moving the wrist, execute these steps
sequentially in a different terminal (allow Gazebo to run unpaused):

```bash
source /opt/ros/jazzy/setup.bash
source ~/dual_chess_ws_v1_3_3_3/install/setup.bash

# A. Positive slide, Robot 1 — target 0.020 m
ros2 topic pub --once /robot1/gripper_finger_joint/cmd_pos std_msgs/msg/Float64 '{data: 0.02}'
sleep 3
ros2 topic echo /joint_states --once

# B. Reverse slide to open — target 0.000 m
ros2 topic pub --once /robot1/gripper_finger_joint/cmd_pos std_msgs/msg/Float64 '{data: 0.0}'
sleep 3
ros2 topic echo /joint_states --once

# C. Repeat both commands with /robot2/gripper_finger_joint/cmd_pos
# D. Only AFTER the reverse-slide test passes: move joint3, then repeat A-B.
```

Accept ONLY if each gripper reads near 0.02 m and returns near 0.00 m;
then remains controllable after its wrist moves (no 0.045 m lockup).
Also check Gazebo and RViz visuals, the two CAD arms, checkerboard and that
`/chess/state` and `/chess/auto/status` remain available.
If any position sticks at 0.045, retain v1.3.2.2 as the verified baseline;
**do not claim success** or merge for the team.

---

# Dual Chess Workspace v1.3.3.2 — CAD-Style Wrist and Collision-Free Home Candidate

Based strictly on v1.3.3.1 (which was built on the verified v1.3.2.2 board baseline).

This candidate updates ONLY the **temporary** wrist / gripper appearance and the
**temporary wrist joint3 neutral mounting transform**. The unchanged original
CAD links `link0.STL`, `link1.STL`, `link2.STL`, the 40 cm checkerboard,
original CAD joints and validated Home settings for base / shoulder / elbow are retained.

- New rounded tapered `temporary_wrist.stl` for each arm, coloured blue/orange
  through the existing Xacro materials, to match the rounded CAD arms better.
- Compact dark `temporary_gripper_fixed.stl` and `temporary_gripper_moving.stl`.
- Wrist mount `joint3` rpy now `0 0 ${pi/2 + 1.0}`. Joint3 at **0 rad** is a
  separated PARK position (not a calibrated mechanical zero). Both wrist tips
  stay on their respective sides of the 40 cm chessboard at startup.
- ROS command topics, ten bridges, Gazebo plugins and controller home values
  remain **unchanged**. The gripper test command continues to use meters.
- This is not a collision-validated motion plan. Running two arms simultaneously
  could still collide; a dual-arm safety planner is required.

**Important:** These meshes are temporary visualization geometry, NOT the final
3D printing STL or a validated mechanical design. Do not replace real motor
specifications, structural calculations or professional safety controls with them.

## Run

```bash
cd ~/dual_chess_ws_v1_3_3_2
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

No extra environment wrappers are needed beyond the baseline dependencies.

## Verify after launch

```bash
ros2 topic echo /joint_states --once
ros2 topic echo /chess/state --once
ros2 topic echo /chess/auto/status --once
```

Check both arms appear and their grippers remain separated over the board,
then move **one wrist at a time** to a small angle in simulation and inspect
`robot1_joint3` and `robot2_joint3` within `/joint_states`.

## Notes

The original v1.3.3.1 contained inter-arm overlap of the long wrist links at
neutral, not a ROS graph failure. Changing the temporary joint3 neutral frame
rather than relying on a startup command reduces the chance of this overlap
before controllers engage. Original Board CAD mesh and 64 coloured squares
are preserved. ROS 2 / Gazebo GUI runtime verification is required on the
team's actual Jazzy machine prior to adoption.

---

# Dual Chess ROS 2 Workspace v1.3.3.1 — Wrist Mount Alignment Fix

**Candidate only.** This patch corrects the wrist mount orientation found after the v1.3.3 visual test; it does not add motors or change CAD geometry.

**Patch v1.3.3.1:** `robotN_joint3` mount is now `rpy="0 0 ${pi/2}"` instead of `rpy="0 ${pi} 0"`. The old rotation folded the extension back over CAD link2. The new one points the extension inward and downward at the tested Home Pose. Position and orientation are still provisional and must be verified visually and through joint-state feedback on Gazebo.

**Candidate only.** Built on the v1.3.2.2 source, which the team tested on ROS 2 Jazzy / Gazebo / RViz.
The original CAD STL arms, 40 cm board STL, 8×8 black/white squares, tested 3-axis Home values,
Chess Brain, Auto Coordinator, bringup and gazebo world were retained.

## Run (Ubuntu 24.04 / ROS 2 Jazzy)

```bash
cd ~/dual_chess_ws_v1_3_3_1
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 launch dual_chess_bringup simulation.launch.py
```

On subsequent runs, the build step can be omitted. Stockfish must be installed at
`/usr/games/stockfish`; ROS Jazzy, ros_gz, Gazebo, Xacro and colcon are system prerequisites.
Python `chess` is provided by the existing Chess Brain build packaging.

## What changed since v1.3.2.2

- Preserved the 3 original actuated joints per CAD arm, transforms and original STLs.
- Appended a **temporary** fourth articulated joint `robotN_joint3` near the end of CAD link2.
- Added `robotN_link3` (a 17 cm wrist/extension) and a small palm, one static finger and one sliding finger.
- Added sliding joint `robotN_gripper_finger_joint` (0 m = open, 0.050 m = test closed).
- Added reference `robotN_tool0` for future IK/robot executor integration.
- Added corresponding Gazebo position controllers and ROS–GZ bridge commands.
- **No motor CAD or fabricated stepper torque specs** in this version. The board,
  markers, CAD STL visuals and HOME `[1.570796, 1.15, 0.35]` remain unchanged.
- The Xacro joints are appended **after** the original CAD chain rather than
  introducing a motor-stator link upstream. This avoids the missing parent frame
  failure of the abandoned v1.4 trial.

### Joint controls per arm

| Topic suffix | Type | Unit | Safe test target |
|---|---|---|---|
| `/base_yaw_joint/cmd_pos` | continuous | rad | keep HOME 1.5708 |
| `/joint1/cmd_pos` | continuous | rad | keep HOME 1.15 |
| `/joint2/cmd_pos` | continuous | rad | keep HOME 0.35 |
| `/joint3/cmd_pos` | revolute | rad | 0.10 (then 0.0) |
| `/gripper_finger_joint/cmd_pos` | prismatic | **meters** | 0.02 (then 0.0) |

Both `robot1` and `robot2` have these topics.

### Verify in a second terminal

```bash
source /opt/ros/jazzy/setup.bash
source ~/dual_chess_ws_v1_3_3_1/install/setup.bash
ros2 node list
ros2 topic echo /joint_states --once
ros2 topic echo /chess/state --once
ros2 topic echo /chess/auto/status --once
```

Expect **11** joint names in `/joint_states`: board joint, plus 5 per arm.
Existing Home targets should still be `[pi/2, 1.15, 0.35]` for both arms;
`joint3=0`, `gripper_finger_joint=0` after initial settling.
`chess_auto_coordinator` must remain `enabled=false`, `mode=passive`.

If the model fails to spawn, Gazebo prints SDF pose graph errors, or a new
controller does not reach its target, **stop and retain v1.3.2.2**.

## Important limitations

- Extension and gripper are provisional visual + simulated kinematic geometry,
  **not** a finalized SolidWorks/3D-print design or tested grasp.
- The original CAD links' inertial values remain unchanged. The new link and finger
  masses/inertias are illustrative and will require final CAD mass properties.
- Joint3's temporary motion limit is ±1.2 rad; true physical limits and servo/stepper
  torque/velocity limits must be designed and verified before hardware use.
- Full 64-square reachability, vertical gripper approach, collision-free planning,
  motor sizing, two-arm safety, and autonomous execution are NOT validated.
- The board STL is as supplied, frame 40×40 cm; active grid 35×35 cm (4.375 cm squares).
- Checkerboard square display is maintained in Gazebo and RViz via fixed visual links.
- No actual chess vision, motor hardware, planning or grasping is connected yet.

## Design/implementation boundaries

Five ROS 2 packages are unchanged in count:
`dual_chess_description` (new arm chain), `dual_chess_gazebo` (bridge update),
`dual_chess_bringup` (unchanged), `chess_brain_handover` (unchanged),
`chess_auto_coordinator` (unchanged).

The standard ROS command remains:
`ros2 launch dual_chess_bringup simulation.launch.py`.
