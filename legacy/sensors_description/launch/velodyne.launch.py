import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Declare arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_rviz",
            default_value="false",
            description="Start RViz2 automatically with this launch file.",
        )
    )

    # Initialize Arguments
    use_rviz = LaunchConfiguration("use_rviz")

    # Launch Velodyne Driver and PointCloud Transform
    launch_velodyne = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('velodyne_driver'), 'launch', 'velodyne_driver_node-VLP16-launch.py')
        )
    )

    launch_velodyne_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('velodyne_pointcloud'), 'launch', 'velodyne_transform_node-VLP16-launch.py')
        )
    )


    # Pointcloud to Laserscan Node
    pointcloud_to_laser = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        remappings=[('cloud_in', 'velodyne_points'), ('scan', 'scan')],
        parameters=[{
            'target_frame': 'velodyne',
            'transform_tolerance': 0.05,
            'min_height': 0.0,
            'max_height': 1.0,
            'angle_min': -3.1415,
            'angle_max': 3.1415,
            'angle_increment': 0.0174,
            'scan_time': 0.1,
            'range_min': 0.45,
            'range_max': 70.0,
            'use_inf': True,
            'inf_epsilon': 1.0
        }],
        name='pointcloud_to_laserscan',
    )
    
    # RViz Configuration
    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("logistic_description"), "rviz", "velodyne.rviz"]
    )

    rviz_node = Node(
       package="rviz2",
       executable="rviz2",
       name="rviz2",
       output="log",
       arguments=["-d", rviz_config_file],
       condition=IfCondition(use_rviz),
    )

    # Define the order of launch actions
    nodes = [
        launch_velodyne,
        launch_velodyne_driver,
        pointcloud_to_laser,
        rviz_node,
    ]

    return LaunchDescription(declared_arguments + nodes)
