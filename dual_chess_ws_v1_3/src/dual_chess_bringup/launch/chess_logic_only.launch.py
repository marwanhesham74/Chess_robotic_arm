"""Start only the chess brain and passive coordinator; no Gazebo, robot or RViz."""
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
    chess_share = get_package_share_directory('chess_brain_handover')
    return LaunchDescription([
        DeclareLaunchArgument('stockfish_path', default_value='/usr/games/stockfish'),
        DeclareLaunchArgument('white_preset', default_value='strong'),
        DeclareLaunchArgument('black_preset', default_value='medium'),
        DeclareLaunchArgument('auto_coordinator_enabled', default_value='true'),
        DeclareLaunchArgument('auto_play_enabled', default_value='false'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(chess_share, 'launch', 'chess_brain.launch.py')),
            launch_arguments={
                'engine_path': LaunchConfiguration('stockfish_path'),
                'white_preset': LaunchConfiguration('white_preset'),
                'black_preset': LaunchConfiguration('black_preset'),
            }.items(),
        ),
        Node(
            package='chess_auto_coordinator', executable='auto_game_coordinator',
            name='chess_auto_coordinator', output='screen',
            parameters=[{'enabled': ParameterValue(
                LaunchConfiguration('auto_play_enabled'), value_type=bool)}],
            condition=IfCondition(LaunchConfiguration('auto_coordinator_enabled')),
        ),
    ])
