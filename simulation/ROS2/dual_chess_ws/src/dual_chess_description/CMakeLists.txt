cmake_minimum_required(VERSION 3.8)
project(dual_chess_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf launch rviz meshes
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/check_urdf_structure.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
