"""Gazebo Harmonic simulation of the dual-arm chess robot (Week-1 foundation).

Starts: gz sim (chess_world.sdf), robot_state_publisher (sim time), ros_gz_sim `create`
(spawns the URDF from /robot_description as model "dual_chess"), ros_gz_bridge
(/clock, /joint_states, /robotN/base_yaw_joint/cmd_pos,
 /robotN/joint1/cmd_pos, /robotN/joint2/cmd_pos).
RViz is NOT started here; use dual_chess_bringup simulation.launch.py for both.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription, TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (Command, FindExecutable, LaunchConfiguration,
                                  PathJoinSubstitution)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

WORLD_NAME = 'chess_world'   # must match worlds/chess_world.sdf and config/bridge.yaml
MODEL_NAME = 'dual_chess'    # must match config/bridge.yaml


def generate_launch_description():
    desc_share = get_package_share_directory('dual_chess_description')
    gz_share = get_package_share_directory('dual_chess_gazebo')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    world = os.path.join(gz_share, 'worlds', 'chess_world.sdf')
    bridge_cfg = os.path.join(gz_share, 'config', 'bridge.yaml')
    xacro_file = PathJoinSubstitution(
        [FindPackageShare('dual_chess_description'), 'urdf', 'dual_chess.urdf.xacro'])

    declared = [
        DeclareLaunchArgument('gz_args', default_value='-r',
                              description="Extra gz sim flags, e.g. '-r -s' (headless server)"),
        DeclareLaunchArgument('robot1_enabled', default_value='true'),
        DeclareLaunchArgument('robot2_enabled', default_value='true'),
        DeclareLaunchArgument('use_meshes', default_value='false'),
        DeclareLaunchArgument('spawn_delay', default_value='3.0',
                              description='Seconds to wait for gz sim before spawning'),
    ]

    # let Gazebo resolve package://dual_chess_description/meshes/robot_arm/*.STL
    resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.dirname(desc_share))

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': ['-v 2 ', LaunchConfiguration('gz_args'), ' ', world],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    robot_description = ParameterValue(
        Command([
            FindExecutable(name='xacro'), ' ', xacro_file,
            ' robot1_enabled:=', LaunchConfiguration('robot1_enabled'),
            ' robot2_enabled:=', LaunchConfiguration('robot2_enabled'),
            ' use_meshes:=', LaunchConfiguration('use_meshes'),
            ' sim_gazebo:=true',
        ]),
        value_type=str,
    )

    rsp = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
    )

    spawn = TimerAction(
        period=LaunchConfiguration('spawn_delay'),
        actions=[Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=['-world', WORLD_NAME, '-name', MODEL_NAME,
                       '-topic', 'robot_description'],
        )],
    )

    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge', output='screen',
        parameters=[{'config_file': bridge_cfg}],
    )

    return LaunchDescription(declared + [resource_path, gz_sim, rsp, spawn, bridge])
