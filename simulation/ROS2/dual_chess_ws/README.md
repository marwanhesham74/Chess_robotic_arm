# Dual Chess Robot — ROS 2 Workspace

## 1. Overview

This workspace contains the ROS 2 packages used to describe, visualize, and simulate the Dual Chess Robot project.

The workspace includes robot description files, CAD-based robot arm models, RViz configurations, Gazebo simulation files, and launch files.

## 2. Workspace Structure

```text
dual_chess_ws/
├── src/
│   ├── dual_chess_description/
│   ├── dual_chess_gazebo/
│   └── dual_chess_bringup/
├── docs/
├── README.md
└── CHANGELOG.md
```

- `dual_chess_description`: URDF/Xacro robot descriptions, meshes, RViz configuration, and visualization launch files.
- `dual_chess_gazebo`: Gazebo launch files, simulation world, and bridge configuration.
- `dual_chess_bringup`: Launch files for bringing up the simulation.
- `docs`: Research, architecture, verification notes, and simulation screenshots.

## 3. Requirements

- Ubuntu with ROS 2 Jazzy installed.
- `colcon` build tools.
- The ROS 2 dependencies required by the workspace packages.

Install the common build tools if needed:

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions
```

Install package dependencies before building:

```bash
cd ~/Chess_robotic_arm/simulation/ROS2/dual_chess_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

If the repository is cloned into a different location, adjust the workspace path accordingly.

## 4. Build the Workspace

From the workspace directory:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --base-paths src
source install/setup.bash
```

The `build/`, `install/`, and `log/` directories are generated locally and are not intended to be committed to Git.

## 5. Launch RViz — CAD Model

To display the CAD-based robot description in RViz:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Chess_robotic_arm/simulation/ROS2/dual_chess_ws
source install/setup.bash
ros2 launch dual_chess_description display_cad.launch.py
```

## 6. Launch Gazebo — CAD Simulation

To launch the CAD-based Gazebo simulation:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Chess_robotic_arm/simulation/ROS2/dual_chess_ws
source install/setup.bash
ros2 launch dual_chess_gazebo gazebo_cad.launch.py
```

Run RViz and Gazebo in separate terminals when testing them independently. Source the ROS 2 and workspace setup files in each terminal.

## 7. Other Available Launch Files

- `dual_chess_description display.launch.py`: standard robot visualization.
- `dual_chess_gazebo gazebo.launch.py`: standard Gazebo launch.
- `dual_chess_bringup simulation.launch.py`: simulation bringup entry point.

The CAD-specific launch files use the exported robot meshes. The standard and CAD-based configurations may differ.

## 8. Troubleshooting

### Package not found

Rebuild the workspace and source it again:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --base-paths src
source install/setup.bash
```

### Meshes are missing

Check that the STL files are present in:

```text
src/dual_chess_description/meshes/robot_arm/
```

Also check the mesh paths referenced by the URDF/Xacro files.

### Launch file not found

List the launch files installed with the packages:

```bash
ros2 pkg prefix dual_chess_description
ros2 pkg prefix dual_chess_gazebo
```

Check the package's `launch/` directory and review any error messages.

## 9. Documentation

See the `docs/` directory for:

- Week 1 checklist and research.
- System architecture.
- Verification and troubleshooting notes.
- Week 1 report and RViz/Gazebo screenshots.

## 10. Project Status

The CAD visualization and CAD-specific launch workflow have been tested in the development workspace. Rebuild and verify the workspace on the target machine before further integration or hardware deployment.

