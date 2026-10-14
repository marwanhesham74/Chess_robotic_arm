# Changelog

This file records the notable changes to the Dual Chess ROS 2 workspace.

## Current Repository Preparation

### Added
- Added the `dual_chess_description` ROS 2 package.
- Added the `dual_chess_gazebo` ROS 2 package.
- Added the `dual_chess_bringup` ROS 2 package.
- Added CAD mesh files for the robot arm.
- Added CAD-specific URDF/Xacro descriptions.
- Added RViz and Gazebo launch configurations for the CAD model.
- Added the Gazebo chess world and bridge configuration.
- Added workspace documentation, verification notes, and screenshots.
- Added build and launch instructions to the workspace README.

### Verified
- Built the workspace from its source packages.
- Tested the CAD visualization launch in RViz.
- Tested the CAD-specific Gazebo launch.

### Repository Cleanup
- Keep source files and documentation in Git.
- Exclude generated `build/`, `install/`, and `log/` directories.
- Replace the old workspace ZIP with the directly accessible workspace files.

### Notes
This entry documents the current repository preparation. It is not a list of historical Git commits.
