# File: launch/mvp_system.launch.py

from __future__ import annotations

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    # TODO: Adjust package names and executables when packaging is set up
    # (e.g., after creating package.xml and setup.py for each Python package).
    # For now, these reflect intended ROS 2 nodes:

    slam_node = Node(
        package="slam_pycu_interface",  # TODO: ensure ROS2 packaging
        executable="slam_node",         # TODO: entry point name in setup.py
        name="slam_node",
        output="screen",
        parameters=[
            {"config_path": "config/slam_config.yaml"},  # TODO: use package share path
        ],
        # TODO: remap camera topic if needed, e.g., ("/camera/image", "/camera/image_raw")
        # remappings=[...]
    )

    wifi_node = Node(
        package="wifi_monitor",         # TODO: ensure ROS2 packaging
        executable="wifi_monitor_node", # TODO: entry point name in setup.py
        name="wifi_monitor",
        output="screen",
        parameters=[
            {"config_path": "config/wifi_config.yaml"},
        ],
    )

    fusion_node = Node(
        package="fusion_logger",        # TODO: ensure ROS2 packaging
        executable="fusion_logger_node",# TODO: entry point name in setup.py
        name="fusion_logger",
        output="screen",
        parameters=[
            {"log_dir": "logs"},
        ],
    )

    return LaunchDescription([
        slam_node,
        wifi_node,
        fusion_node,
    ])

