from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory
from limo_mycobot_control.description_builder import build_robot_description

import os


def _launch_setup(context):
    mount_x = float(LaunchConfiguration("arm_mount_x").perform(context))
    mount_y = float(LaunchConfiguration("arm_mount_y").perform(context))
    mount_z = float(LaunchConfiguration("arm_mount_z").perform(context))
    mount_roll = float(LaunchConfiguration("arm_mount_roll").perform(context))
    mount_pitch = float(LaunchConfiguration("arm_mount_pitch").perform(context))
    mount_yaw = float(LaunchConfiguration("arm_mount_yaw").perform(context))
    robot_description = build_robot_description(
        mount_x, mount_y, mount_z, mount_roll, mount_pitch, mount_yaw
    )

    rviz_enabled = LaunchConfiguration("rviz").perform(context).lower() in ("true", "1", "yes")
    start_limo = LaunchConfiguration("start_limo_driver").perform(context).lower() in ("true", "1", "yes")

    actions = []
    if start_limo:
        limo_share = get_package_share_directory("limo_base")
        limo_launch = os.path.join(limo_share, "launch", "limo_base.launch.py")
        actions.append(
            IncludeLaunchDescription(PythonLaunchDescriptionSource(limo_launch))
        )

    actions.extend([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description, "publish_frequency": 30.0}],
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            name="joint_state_publisher_gui",
            output="screen",
            parameters=[{"robot_description": robot_description}],
            remappings=[("/joint_states", "/joint_states_cmd")],
        ),
        Node(
            package="limo_mycobot_control",
            executable="joint_slider_bridge",
            name="limo_mycobot_joint_slider_bridge",
            output="screen",
            parameters=[{
                "port": LaunchConfiguration("port"),
                "baud": LaunchConfiguration("baud"),
                "arm_speed": LaunchConfiguration("arm_speed"),
                "arm_enabled": LaunchConfiguration("arm_enabled"),
                "base_enabled": LaunchConfiguration("base_enabled"),
                "odom_topic": LaunchConfiguration("odom_topic"),
                "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                "max_linear_speed": LaunchConfiguration("max_linear_speed"),
                "max_angular_speed": LaunchConfiguration("max_angular_speed"),
            }],
        ),
    ])

    if rviz_enabled:
        rviz_file = os.path.join(
            get_package_share_directory("limo_mycobot_control"), "rviz", "limo_mycobot.rviz"
        )
        actions.append(
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", rviz_file],
                output="screen",
            )
        )
    return actions


def generate_launch_description():
    args = [
        DeclareLaunchArgument("port", default_value="/dev/ttyUSB0", description="MyCobot 280 M5 serial port. Use /dev/ttyACM0 if applicable."),
        DeclareLaunchArgument("baud", default_value="115200", description="MyCobot M5 baud rate."),
        DeclareLaunchArgument("arm_speed", default_value="20", description="Arm movement speed (1-100 percent). Start slowly."),
        DeclareLaunchArgument("arm_enabled", default_value="true", description="Enable MyCobot serial commands."),
        DeclareLaunchArgument("base_enabled", default_value="true", description="Enable LIMO cmd_vel controller."),
        DeclareLaunchArgument("odom_topic", default_value="/wheel/odom", description="LIMO odometry topic."),
        DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel", description="LIMO velocity command topic."),
        DeclareLaunchArgument("max_linear_speed", default_value="0.08", description="Maximum base linear speed (m/s)."),
        DeclareLaunchArgument("max_angular_speed", default_value="0.35", description="Maximum base yaw speed (rad/s)."),
        DeclareLaunchArgument("start_limo_driver", default_value="true", description="Start limo_base/limo_base.launch.py from this launch."),
        DeclareLaunchArgument("arm_mount_x", default_value="0.0", description="Arm mount X offset from top-plate centre (m)."),
        DeclareLaunchArgument("arm_mount_y", default_value="0.0", description="Arm mount Y offset from top-plate centre (m)."),
        DeclareLaunchArgument("arm_mount_z", default_value="0.205", description="Arm base height above floor/odom origin (m)."),
        DeclareLaunchArgument("arm_mount_roll", default_value="0.0", description="Arm mount roll (rad)."),
        DeclareLaunchArgument("arm_mount_pitch", default_value="0.0", description="Arm mount pitch (rad)."),
        DeclareLaunchArgument("arm_mount_yaw", default_value="0.0", description="Arm mount yaw (rad)."),
        DeclareLaunchArgument("rviz", default_value="true", description="Start RViz."),
    ]
    return LaunchDescription(args + [OpaqueFunction(function=_launch_setup)])
