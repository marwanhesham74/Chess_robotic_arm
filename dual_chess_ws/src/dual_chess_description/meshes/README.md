# Meshes (intentionally empty in Week 1)

Week 1 uses primitive boxes/cylinders. Real CAD arrives from M1 in Week 2
("Prepare meshes for export to M6").

Expected layout (file stem == link name WITHOUT the robot prefix):

    meshes/visual/arm/base_link.stl      (or .dae)
    meshes/visual/arm/link1.stl ... link5.stl, gripper_link.stl
    meshes/collision/arm/<same names>.stl      (simplified / convex)

Ask M1 for:
- Units: metres (otherwise set `arm_mesh_scale` in urdf/arm/arm_params_placeholder.xacro)
- Mesh origin == that link's URDF frame (NOT the CAD assembly origin)
- Collision meshes: low-poly / convex, never the full-detail visual mesh
- ONE set of meshes: robot1 and robot2 share them (robot2 is a placed copy)

Switch from primitives to meshes with the xacro argument  use_meshes:=true
(launch files forward it). Resolved via package://dual_chess_description/meshes/...
