#!/usr/bin/env bash
# Optional ONE-TIME preparation for a fresh Ubuntu 24.04 machine with ROS 2 Jazzy.
# Not called by colcon and not needed if the device already has ROS/Gazebo/Stockfish.
# Never touches NVIDIA drivers directly, never runs upgrade/autoremove/dpkg repair.
set -Eeuo pipefail
if [[ "${EUID}" == 0 ]]; then
  echo 'Run this as a regular user. sudo is used only for apt install.' >&2
  exit 2
fi
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo 'ROS 2 Jazzy is missing. Install it first from:' >&2
  echo 'https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html' >&2
  exit 2
fi
cat <<'TEXT'
This ONE-TIME optional command installs missing OS/ROS prerequisites through apt.
It does not install python-chess (the chess_brain package does that during build).
It will NOT upgrade/autoremove packages or change NVIDIA packages directly.
TEXT
packages=(
  stockfish python3-pip python3-colcon-common-extensions
  ros-jazzy-ros-gz ros-jazzy-xacro
  ros-jazzy-robot-state-publisher ros-jazzy-rviz2
  ros-jazzy-joint-state-publisher ros-jazzy-joint-state-publisher-gui
)
missing=()
for package in "${packages[@]}"; do
  if ! dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null | grep -qx installed; then
    missing+=("$package")
  fi
done
if (( ${#missing[@]} == 0 )); then
  echo 'OS/ROS prerequisites already installed. No apt changes required.'
  exit 0
fi
if [[ -n "$(dpkg --audit)" ]]; then
  echo 'BLOCKED: dpkg has broken/unconfigured packages.' >&2
  echo 'Do not run an automatic apt command. Repair dpkg/kernel/NVIDIA separately first.' >&2
  dpkg --audit >&2
  exit 3
fi
printf 'Missing: %s\n' "${missing[*]}"
read -r -p 'Install these packages with sudo apt install? [y/N] ' answer
if [[ "$answer" != 'y' && "$answer" != 'Y' ]]; then
  echo 'Cancelled; no changes made.'
  exit 0
fi
sudo apt install --no-install-recommends "${missing[@]}"
