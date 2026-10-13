"""Display the dual-arm chess robot in RViz (no Gazebo).

Starts: robot_state_publisher, joint_state_publisher_gui (or the non-GUI one), rviz2.
Use this to check URDF/Xacro, TF and joint motion before involving Gazebo.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import (Command, FindExecutable, LaunchConfiguration,
                                  PathJoinSubstitution)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('dual_chess_description')
    xacro_file = PathJoinSubstitution([pkg, 'urdf', 'dual_chess.urdf.xacro'])
    rviz_config = PathJoinSubstitution([pkg, 'rviz', 'dual_chess.rviz'])

    declared = [
        DeclareLaunchArgument('gui', default_value='true',
                              description='Open joint_state_publisher_gui sliders'),
        DeclareLaunchArgument('rviz', default_value='true', description='Start RViz'),
        DeclareLaunchArgument('robot1_enabled', default_value='true'),
        DeclareLaunchArgument('robot2_enabled', default_value='true'),
        DeclareLaunchArgument('use_meshes', default_value='false',
                              description='Use CAD meshes (needs files from M1)'),
    ]

    robot_description = ParameterValue(
        Command([
            FindExecutable(name='xacro'), ' ', xacro_file,
            ' robot1_enabled:=', LaunchConfiguration('robot1_enabled'),
            ' robot2_enabled:=', LaunchConfiguration('robot2_enabled'),
            ' use_meshes:=', LaunchConfiguration('use_meshes'),
            ' sim_gazebo:=false',
        ]),
        value_type=str,
    )

    rsp = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen', parameters=[{'robot_description': robot_description}],
    )
    jsp_gui = Node(
        package='joint_state_publisher_gui', executable='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('gui')),
    )
    jsp = Node(
        package='joint_state_publisher', executable='joint_state_publisher',
        condition=UnlessCondition(LaunchConfiguration('gui')),
    )
    rviz = Node(
        package='rviz2', executable='rviz2', arguments=['-d', rviz_config],
        output='screen', condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription(declared + [rsp, jsp_gui, jsp, rviz])
