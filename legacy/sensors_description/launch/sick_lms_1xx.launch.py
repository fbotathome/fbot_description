import os
import sys
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration


def generate_launch_description():

    sick_scan_pkg_prefix = get_package_share_directory('sensors_description')
    launchfile = os.path.basename(__file__)[:-3] # convert "<lidar_name>.launch.py" to "<lidar_name>.launch"
    launch_file_path = os.path.join(sick_scan_pkg_prefix, 'launch/' + launchfile) # 'launch/sick_lms_1xx.launch')
    node_arguments=[launch_file_path]
    
    for arg in sys.argv:
    # append optional commandline arguments in name:=value syntax
        if len(arg.split(":=")) == 2:
            node_arguments.append(arg)
    
    ROS_DISTRO = os.environ.get('ROS_DISTRO') # i.e. 'eloquent', 'foxy', etc.
    if ROS_DISTRO[0] <= "e": # ROS versions eloquent and earlier require "node_executable", ROS foxy and later use "executable"
        node = Node(
            package='sick_scan_xd',
            node_executable='sick_generic_caller',
            output='screen',
            arguments=node_arguments
        )
    else: # ROS versions eloquent and earlier require "node_executable", ROS foxy and later use "executable"
        node = Node(
            package='sick_scan_xd',
            executable='sick_generic_caller',
            output='screen',
            arguments=node_arguments
        )
    
    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            arguments=['-d', os.path.join(sick_scan_pkg_prefix, 'rviz', 'sick_lms_1xx.rviz')]
        )

    launch_args=DeclareLaunchArgument(
            'use_rviz',
            default_value='False'
        )


    return LaunchDescription(
        [
            launch_args,
            rviz_node,
            node,
            
        ]
    )
#    ld.add_action(launch_args)
#    ld.add_action(rviz_node, node)
#    return ld
