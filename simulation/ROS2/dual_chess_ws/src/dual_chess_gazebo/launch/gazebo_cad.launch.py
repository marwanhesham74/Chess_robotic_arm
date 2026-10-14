import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    desc_share = get_package_share_directory('dual_chess_description')
    gazebo_share = get_package_share_directory('dual_chess_gazebo')
    ros_gz_share = get_package_share_directory('ros_gz_sim')

    world = os.path.join(gazebo_share, 'worlds', 'chess_world.sdf')
    xacro_file = PathJoinSubstitution([
        FindPackageShare('dual_chess_description'),
        'urdf', 'dual_chess_cad.urdf.xacro'
    ])

    resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.dirname(desc_share)
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': ['-v 2 ', world],
        }.items(),
    )

    robot_description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' ', xacro_file]),
        value_type=str,
    )

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
        output='screen',
    )

    spawn = TimerAction(
        period=3.0,
        actions=[Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-world', 'chess_world',
                '-name', 'dual_chess_cad',
                '-topic', 'robot_description',
            ],
            output='screen',
        )],
    )

    return LaunchDescription([resource_path, gazebo, rsp, spawn])
