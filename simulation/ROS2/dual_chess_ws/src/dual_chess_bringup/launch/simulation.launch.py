"""One command: Gazebo world + both robots + bridge + RViz (using simulated joint states)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gz_share = get_package_share_directory('dual_chess_gazebo')
    desc_share = get_package_share_directory('dual_chess_description')

    declared = [
        DeclareLaunchArgument('rviz', default_value='true', description='Start RViz'),
        DeclareLaunchArgument('gz_args', default_value='-r'),
        DeclareLaunchArgument('robot1_enabled', default_value='true'),
        DeclareLaunchArgument('robot2_enabled', default_value='true'),
        DeclareLaunchArgument('use_meshes', default_value='false'),
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

    return LaunchDescription(declared + [gazebo, rviz])
