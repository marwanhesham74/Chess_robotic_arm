"""One command: Gazebo world + both robots + bridge + RViz (using simulated joint states)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    gz_share = get_package_share_directory('dual_chess_gazebo')
    desc_share = get_package_share_directory('dual_chess_description')
    chess_share = get_package_share_directory('chess_brain_handover')

    declared = [
        DeclareLaunchArgument('rviz', default_value='true', description='Start RViz'),
        DeclareLaunchArgument('gz_args', default_value='-r'),
        DeclareLaunchArgument('robot1_enabled', default_value='true'),
        DeclareLaunchArgument('robot2_enabled', default_value='true'),
        DeclareLaunchArgument('use_meshes', default_value='false'),
        DeclareLaunchArgument('chess_brain_enabled', default_value='true',
                              description='Launch Stockfish chess logic (no arm control)'),
        DeclareLaunchArgument('auto_coordinator_enabled', default_value='true',
                              description='Launch passive-by-default coordinator node'),
        DeclareLaunchArgument('auto_play_enabled', default_value='false',
                              description='OFF by default: no automatic game commands'),
        DeclareLaunchArgument('stockfish_path', default_value='/usr/games/stockfish'),
        DeclareLaunchArgument('white_preset', default_value='strong'),
        DeclareLaunchArgument('black_preset', default_value='medium'),
    ]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gz_share, 'launch', 'gazebo.launch.py')),
        launch_arguments={
            'gz_args': LaunchConfiguration('gz_args'),
            'robot1_enabled': LaunchConfiguration('robot1_enabled'),
            'robot2_enabled': LaunchConfiguration('robot2_enabled'),
            'use_meshes': LaunchConfiguration('use_meshes'),
        }.items(),
    )

    rviz = Node(
        package='rviz2', executable='rviz2', output='screen',
        arguments=['-d', os.path.join(desc_share, 'rviz', 'dual_chess.rviz')],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    # Existing Gazebo + RViz actions above are untouched. Two *additional*
    # high-level ROS nodes are launched without fake vision/robot executors.
    chess_brain = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(chess_share, 'launch', 'chess_brain.launch.py')),
        launch_arguments={
            'engine_path': LaunchConfiguration('stockfish_path'),
            'white_preset': LaunchConfiguration('white_preset'),
            'black_preset': LaunchConfiguration('black_preset'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('chess_brain_enabled')),
    )

    auto_coordinator = Node(
        package='chess_auto_coordinator', executable='auto_game_coordinator',
        name='chess_auto_coordinator', output='screen',
        parameters=[{'enabled': ParameterValue(
            LaunchConfiguration('auto_play_enabled'), value_type=bool)}],
        condition=IfCondition(LaunchConfiguration('auto_coordinator_enabled')),
    )

    return LaunchDescription(declared + [gazebo, rviz, chess_brain, auto_coordinator])
