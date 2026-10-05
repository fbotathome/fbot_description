import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetLaunchConfiguration, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    urg_node_dir = get_package_share_directory('sensors_description')

    return LaunchDescription([
        # Argumento para escolher a interface do sensor (serial ou ethernet)
        DeclareLaunchArgument(
            'sensor_interface',
            default_value='serial',
            description='sensor_interface: supported: serial, ethernet'
        ),

        # Argumento para abrir o RViz ou não
        DeclareLaunchArgument(
            'use_rviz',
            default_value='false',
            description='Flag to enable RViz'
        ),

        # Configura o caminho do arquivo de parâmetros baseado na interface do sensor
        OpaqueFunction(function=lambda context: [
            SetLaunchConfiguration(
                'param', os.path.join(
                    urg_node_dir, 'config',
                    'urg_node_' + context.launch_configurations['sensor_interface'] + '.yaml'
                )
            )
        ]),

        # Nó do LIDAR Hokuyo
        Node(
            package='urg_node',
            executable='urg_node_driver',
            name='urg_node_back',
            output='screen',
            parameters=[LaunchConfiguration('param')],
            remappings=[('scan', 'scan3')]
        ),

        # Condicional para abrir o RViz se 'use_rviz' for True
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            arguments=['-d', os.path.join(urg_node_dir, 'rviz', 'urg_node.rviz')]
        )
    ])