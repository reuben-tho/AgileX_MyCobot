from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from limo_mycobot_control.description_builder import build_robot_description


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
    actions = [
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
        ),
    ]
    if rviz_enabled:
        from ament_index_python.packages import get_package_share_directory
        import os
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
        DeclareLaunchArgument("arm_mount_x", default_value="0.0", description="Arm mount X offset from top-plate centre (m)."),
        DeclareLaunchArgument("arm_mount_y", default_value="0.0", description="Arm mount Y offset from top-plate centre (m)."),
        DeclareLaunchArgument("arm_mount_z", default_value="0.205", description="Arm base height above floor/odom origin (m)."),
        DeclareLaunchArgument("arm_mount_roll", default_value="0.0", description="Arm mount roll (rad)."),
        DeclareLaunchArgument("arm_mount_pitch", default_value="0.0", description="Arm mount pitch (rad)."),
        DeclareLaunchArgument("arm_mount_yaw", default_value="0.0", description="Arm mount yaw (rad)."),
        DeclareLaunchArgument("rviz", default_value="true", description="Start RViz."),
    ]
    return LaunchDescription(args + [OpaqueFunction(function=_launch_setup)])
