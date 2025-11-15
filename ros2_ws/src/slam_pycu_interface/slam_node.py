# File: ros2_ws/src/slam_pycu_interface/slam_node.py

from __future__ import annotations

import time
from typing import Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
# from sensor_msgs.msg import Image  # TODO: enable when integrating camera

from .pycu_slam_wrapper import PycuVSLAMManager


class SlamNode(Node):
    """ROS2 node wrapping pycuVSLAM manager.

    - Subscribes to a camera image topic (placeholder; TODO to implement Image->array conversion).
    - Feeds frames to PycuVSLAMManager.
    - Publishes PoseStamped on /slam/pose.
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

        # Publishers
        self._pose_pub = self.create_publisher(PoseStamped, "/slam/pose", 10)
        self._map_points_pub = self.create_publisher(String, "/slam/map_points", 10)

        # Subscriptions (placeholder; uncomment when Image stream is available)
        # self._image_sub = self.create_subscription(
        #     Image,
        #     "/camera/image_raw",
        #     self._on_image,
        #     10,
        # )

        # Optional: timer to publish placeholder map points (empty for now)
        self._mp_timer = self.create_timer(2.0, self._publish_map_points_placeholder)

        self.get_logger().info(f"slam_node initialized with config: {self._config_path}")

    def _on_image(self, msg) -> None:  # msg: Image
        """Image callback.

        TODOs:
        - Convert sensor_msgs/Image to numpy array (e.g., via cv_bridge or manual conversion).
        - Extract timestamp; here we use wall time placeholder.
        - Feed into SLAM and publish pose when available.
        """
        timestamp = time.time()
        image_array = None  # TODO: convert msg to numpy array

        processed: Optional[bool] = self._manager.process_frame(image_array, timestamp)
        if processed:
            pose = self._manager.get_latest_pose()
            if pose is not None:
                self._publish_pose(pose)

    def _publish_pose(self, pose_dict) -> None:
        ps = PoseStamped()
        now = self.get_clock().now().to_msg()
        ps.header.stamp = now
        ps.header.frame_id = "map"  # TODO: frame convention

        # Expecting pose_dict keys: position: (x,y,z), orientation: (w,x,y,z)
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
        # Placeholder publisher for map points; replace with custom msg type later.
        mp = self._manager.get_map_points()
        payload = String()
        payload.data = f"map_points_count={len(mp)}"  # TODO: define proper message
        self._map_points_pub.publish(payload)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SlamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

