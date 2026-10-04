# Contributing Guidelines

## Branches

Do not work directly on the `main` branch.

Create a branch for your task:

```text
mechanical/...
kinematics/...
control/...
integration/...
simulation/...
firmware/...
docs/...
Examples
control/joint-pid
kinematics/inverse-kinematics
mechanical/arm-assembly
integration/ros2-communication
Commits

Use clear commit messages.

Examples
Add inverse kinematics implementation
Update arm CAD assembly
Implement joint PID controller
Add ROS 2 communication node
Update project requirements
Pull Requests

Before merging into main:

Push your branch.
Create a Pull Request.
Explain what was changed.
Make sure the work is tested.
Wait for review.
File Organization

Put files in the appropriate project directory.

Do not place random files in the repository root.

Important

Do not upload:

Build folders
Temporary files
IDE configuration files
Passwords or API keys
Large generated files unless required