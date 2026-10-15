"""Launch Chess Brain's logical ROS interface. Not robot or camera drivers."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("engine_path", default_value="/usr/games/stockfish"),
        DeclareLaunchArgument("white_preset", default_value="strong"),
        DeclareLaunchArgument("black_preset", default_value="medium"),
        Node(
            package="chess_brain_handover", executable="chess_brain_node",
            name="chess_brain", output="screen",
            parameters=[{
                "engine_path": LaunchConfiguration("engine_path"),
                "white_preset": LaunchConfiguration("white_preset"),
                "black_preset": LaunchConfiguration("black_preset"),
                "allow_placement_shortcut": False,
            }],
        ),
    ])
