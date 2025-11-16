# File: launch/mvp_system.launch.py

from __future__ import annotations

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description() -> LaunchDescription:
    # Get the slam_pycu_interface package share directory
    slam_package_dir = get_package_share_directory('slam_pycu_interface')

    slam_node = Node(
        package="slam_pycu_interface",
        executable="slam_node",
        name="slam_node",
        output="screen",
        parameters=[
            {"config_path": f"{slam_package_dir}/../../config/slam_config.yaml"},
        ],
    )

    # TODO: Add wifi_monitor and fusion_logger nodes later
    # For now, focus on SLAM node functionality

    return LaunchDescription([
        slam_node,
    ])

