"""View the BORIS model without any hardware (RViz + joint sliders).

  ros2 launch fbot_description display.launch.py
  ros2 launch fbot_description display.launch.py robot_version:=v2 use_neck:=false

The robot itself is started from fbot_bringup/launch/robot.launch.py.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    args = [
        DeclareLaunchArgument('robot_version', default_value='v1', description='BORIS version (fbot_description/config/robot/<v>.yaml)'),
        DeclareLaunchArgument('use_neck', default_value='true', description='Include neck + camera mount'),
        DeclareLaunchArgument('use_arm_mount', default_value='true', description='Include the arm mounting plate'),
        DeclareLaunchArgument('arm_z_position', default_value='0.315', description='Arm plate height on the torso [m]'),
        DeclareLaunchArgument('use_rviz', default_value='true', description='Start RViz2'),
    ]

    robot_description = {
        'robot_description': ParameterValue(
            Command([
                PathJoinSubstitution([FindExecutable(name='xacro')]), ' ',
                PathJoinSubstitution([FindPackageShare('fbot_description'), 'urdf', 'boris.urdf.xacro']),
                ' robot_version:=', LaunchConfiguration('robot_version'),
                ' use_neck:=', LaunchConfiguration('use_neck'),
                ' use_arm_mount:=', LaunchConfiguration('use_arm_mount'),
                ' arm_z_position:=', LaunchConfiguration('arm_z_position'),
            ]),
            value_type=str,
        )
    }

    return LaunchDescription(args + [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[robot_description], output='both'),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui'),
        Node(package='rviz2', executable='rviz2', output='log',
             arguments=['-d', PathJoinSubstitution([FindPackageShare('fbot_description'), 'rviz', 'boris.rviz'])],
             condition=IfCondition(LaunchConfiguration('use_rviz'))),
    ])
