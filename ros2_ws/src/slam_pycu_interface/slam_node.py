# File: ros2_ws/src/slam_pycu_interface/slam_node.py

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

from .pycu_slam_wrapper import PycuVSLAMManager


class SlamNode(Node):
    """ROS2 node wrapping pycuVSLAM manager.

    - Generates or subscribes to camera image frames (initially mock for testing).
    - Feeds frames to PycuVSLAMManager.
    - Publishes PoseStamped on /slam/pose.
    - Prints x,y,z position to terminal for debugging.
    - Optionally publishes a placeholder map points topic /slam/map_points (String for now).
    """

    def __init__(self) -> None:
        super().__init__("slam_node")

        # Parameters
        self.declare_parameter("config_path", "config/slam_config.yaml")
        self._config_path: str = self.get_parameter("config_path").get_parameter_value().string_value

        # SLAM manager
        self._manager = PycuVSLAMManager(config_path=self._config_path)
        self._manager.initialize_slam()

        # Initialize IMU
        imu_port = self.declare_parameter(
            "imu_port",
            "/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00"
        ).get_parameter_value().string_value
        imu_baud = self.declare_parameter("imu_baud", 115200).get_parameter_value().integer_value
        self._manager.initialize_imu(port=imu_port, baud=imu_baud)

        # Publishers
        self._pose_pub = self.create_publisher(PoseStamped, "/slam/pose", 10)
        self._map_points_pub = self.create_publisher(String, "/slam/map_points", 10)

        # Timer to generate test frames and process them
        self._frame_timer = self.create_timer(0.033, self._on_frame_timer)  # ~30 Hz

        # Timer to publish pose
        self._publish_timer = self.create_timer(0.1, self._on_publish_timer)  # 10 Hz

        # Timer to publish placeholder map points
        self._mp_timer = self.create_timer(2.0, self._publish_map_points_placeholder)

        # Frame counter for mock data
        self._frame_counter = 0

        self.get_logger().info(f"slam_node initialized with config: {self._config_path}")

    def _on_frame_timer(self) -> None:
        """Timer callback to generate or fetch frames and process them."""
        # Generate mock frame data (grayscale image)
        # In production, this would receive from camera topic subscription
        image = self._generate_mock_frame()
        timestamp = time.time()

        # Process frame with SLAM
        processed = self._manager.process_frame(image, timestamp)
        if processed:
            self._frame_counter += 1

    def _generate_mock_frame(self) -> np.ndarray:
        """Generate a mock camera frame for testing.
        
        In production, this would be replaced by actual camera input via subscription.
        This simulates a 640x480 grayscale image with some varying pattern.
        """
        frame_idx = self._frame_counter % 30  # Cycle pattern every 30 frames
        height, width = 480, 640
        
        # Create a simple pattern that changes over time
        image = np.zeros((height, width), dtype=np.uint8)
        
        # Add a moving pattern
        x_center = width // 2 + int(10 * np.sin(frame_idx * 0.2))
        y_center = height // 2 + int(10 * np.cos(frame_idx * 0.2))
        
        # Draw a simple circle in the center
        y, x = np.ogrid[:height, :width]
        mask = (x - x_center) ** 2 + (y - y_center) ** 2 <= 50 ** 2
        image[mask] = 200
        
        # Add some noise
        noise = np.random.randint(0, 50, (height, width), dtype=np.uint8)
        image = np.clip(image.astype(int) + noise.astype(int), 0, 255).astype(np.uint8)
        
        return image

    def _on_publish_timer(self) -> None:
        """Timer callback to publish the latest pose."""
        pose = self._manager.get_latest_pose()
        if pose is not None:
            self._publish_pose(pose)
            # Print position to terminal
            pos = pose.get("position", (0.0, 0.0, 0.0))
            print(f"[SLAM] X: {pos[0]:.4f}, Y: {pos[1]:.4f}, Z: {pos[2]:.4f}")

    def _publish_pose(self, pose_dict) -> None:
        """Publish pose as PoseStamped message.
        
        Args:
            pose_dict: Dict with keys 'position': (x,y,z) and 'orientation': (w,x,y,z)
        """
        ps = PoseStamped()
        now = self.get_clock().now().to_msg()
        ps.header.stamp = now
        ps.header.frame_id = "map"

        # Extract position and orientation
        pos = pose_dict.get("position", (0.0, 0.0, 0.0))
        ori = pose_dict.get("orientation", (1.0, 0.0, 0.0, 0.0))
        
        ps.pose.position.x = float(pos[0])
        ps.pose.position.y = float(pos[1])
        ps.pose.position.z = float(pos[2])
        ps.pose.orientation.w = float(ori[0])
        ps.pose.orientation.x = float(ori[1])
        ps.pose.orientation.y = float(ori[2])
        ps.pose.orientation.z = float(ori[3])

        self._pose_pub.publish(ps)

    def _publish_map_points_placeholder(self) -> None:
        """Publish map points count as placeholder."""
        mp = self._manager.get_map_points()
        payload = String()
        payload.data = f"map_points_count={len(mp)}"
        self._map_points_pub.publish(payload)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SlamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._manager.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

