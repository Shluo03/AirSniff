# File: launch/mvp_system.launch.py

from __future__ import annotations

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    # TODO: Adjust package names and executables when packaging is set up
    # (e.g., after creating package.xml and setup.py for each Python package).
    # For now, these reflect intended ROS 2 nodes:

    # Capture mode: record video + Wi-Fi RSSI (no real-time SLAM)
    video_node = Node(
        package="video_recorder",
        executable="video_recorder_node",
        name="video_recorder",
        output="screen",
        parameters=[
            {"output_dir": "logs/video"},
            {"base_name": "capture"},
            {"fps": 30.0},
            {"topic": "/camera/image_raw"},  # TODO: adjust camera topic
            {"encoding": "mp4v"},
        ],
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

    return LaunchDescription([
        video_node,
        wifi_node,
    ])
