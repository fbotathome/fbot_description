from launch import LaunchDescription
import os
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.parameter_descriptions  import ParameterValue
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

    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("boris_description"), "urdf", "boris_description.xacro"]
            ),
        ]
    )
    robot_description = {"robot_description": ParameterValue(robot_description_content,value_type=str)}

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare("boris_description"),
            "config",
            "boris_controllers.yaml",
        ]
    )

    robot_localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fbot_navigation'), 'launch', 'robot_localization.launch.py')
        )
    )

    interbotix_arm_control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("interbotix_xsarm_control"), 'launch', 'xsarm_control.launch.py')
        ),
        launch_arguments={
            'robot_model': 'wx200',
            'use_rviz': 'false',
            'use_world_frame': 'false',
            'use_sim': 'false',
            'hardware_type': 'actual'
        }.items(),
    )


    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("boris_description"), "rviz", "boris.rviz"]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, robot_controllers],
        output="both",
        remappings=[
            ("/hoverboard_base_controller/cmd_vel_unstamped", "/cmd_vel"),
            ("/hoverboard_base_controller/odom", "/odom"),
            ("~/robot_description", "/robot_description"),
        ],
    )

    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    joint_state_publisher_node = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        output="both",
        parameters=[{
            'source_list': ['/boris_head/joint_states'],
        }],
    )

    static_tf_arm_to_arm_support_joint = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_arm_to_arm_support_joint',
        arguments=['0.1', '0', '0.0235', '0', '0', '0', 'arm_support_link', 'wx200/base_link'],
        output='screen'
    )

    rviz_node = Node(
       package="rviz2",
       executable="rviz2",
       name="rviz2",
       output="log",
       arguments=["-d", rviz_config_file],
       condition=IfCondition(use_rviz),
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["hoverboard_base_controller", "--controller-manager", "/controller_manager"],
    )

    # Delay rviz start after `joint_state_broadcaster`
    delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
       event_handler=OnProcessExit(
           target_action=joint_state_broadcaster_spawner,
           on_exit=[rviz_node],
       )
    )

    # Delay start of robot_controller after `joint_state_broadcaster`
    delay_robot_controller_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[robot_controller_spawner],
        )
    )

    nodes = [
        control_node,
        robot_state_pub_node,
        joint_state_publisher_node,
        joint_state_broadcaster_spawner,
        static_tf_arm_to_arm_support_joint,
        delay_rviz_after_joint_state_broadcaster_spawner,
        delay_robot_controller_spawner_after_joint_state_broadcaster_spawner,
        interbotix_arm_control,
        robot_localization,
    ]

    return LaunchDescription(declared_arguments + nodes)
