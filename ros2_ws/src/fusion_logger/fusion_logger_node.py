# File: ros2_ws/src/fusion_logger/fusion_logger_node.py

from __future__ import annotations

import csv
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String


class FusionLoggerNode(Node):
    """Fuses SLAM poses with Wi‑Fi RSSI and logs to CSV.

    Subscriptions:
    - /slam/pose (geometry_msgs/PoseStamped)
    - /wifi/rssi (String; JSON payload for now)

    Logging:
    - Writes CSV to logs/ with columns:
      timestamp, x, y, z, qw, qx, qy, qz, ssid, bssid, rssi_dbm, channel

    TODOs:
    - Better pose interpolation (not just nearest neighbor).
    - Handle multiple APs/channels more intelligently.
    - Export to 3D visualization-friendly formats (e.g., PLY, JSON).
    """

    def __init__(self) -> None:
        super().__init__("fusion_logger")

        # Parameters
        self.declare_parameter("log_dir", "logs")
        self._log_dir: str = self.get_parameter("log_dir").get_parameter_value().string_value
        os.makedirs(self._log_dir, exist_ok=True)

        # Open CSV
        ts = int(time.time())
        self._csv_path = os.path.join(self._log_dir, f"fused_log_{ts}.csv")
        self._csv_file = open(self._csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._csv_file)
        self._writer.writerow([
            "timestamp",
            "x", "y", "z",
            "qw", "qx", "qy", "qz",
            "ssid", "bssid", "rssi_dbm", "channel",
        ])

        # Pose history buffer (simple)
        self._pose_history: List[Tuple[float, Tuple[float, float, float], Tuple[float, float, float, float]]] = []
        self._max_pose_history = 1000  # TODO: tune

        # Subscriptions
        self.create_subscription(PoseStamped, "/slam/pose", self._on_pose, 50)
        self.create_subscription(String, "/wifi/rssi", self._on_wifi, 50)

        self.get_logger().info(f"fusion_logger writing CSV to {self._csv_path}")

    def _on_pose(self, msg: PoseStamped) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.position
        q = msg.pose.orientation
        pos = (float(p.x), float(p.y), float(p.z))
        ori = (float(q.w), float(q.x), float(q.y), float(q.z))
        self._pose_history.append((t, pos, ori))
        if len(self._pose_history) > self._max_pose_history:
            self._pose_history.pop(0)

    def _on_wifi(self, msg: String) -> None:
        try:
            data = json.loads(msg.data)
        except Exception as e:
            self.get_logger().warn(f"invalid Wi‑Fi JSON: {e}")
            return

        t = float(data.get("timestamp", time.time()))
        ssid = str(data.get("ssid", ""))
        bssid = str(data.get("bssid", ""))
        rssi_dbm = data.get("rssi_dbm")
        channel = data.get("channel")

        pose = self._nearest_pose(t)
        if pose is None:
            # No pose yet; skip logging or consider caching Wi‑Fi to log later
            return

        pt, pos, ori = pose
        self._writer.writerow([
            f"{t:.6f}",
            f"{pos[0]:.6f}", f"{pos[1]:.6f}", f"{pos[2]:.6f}",
            f"{ori[0]:.6f}", f"{ori[1]:.6f}", f"{ori[2]:.6f}", f"{ori[3]:.6f}",
            ssid, bssid, rssi_dbm, channel,
        ])
        # Optionally flush periodically to ensure data is persisted
        # TODO: make flush interval configurable
        self._csv_file.flush()

    def _nearest_pose(self, t: float) -> Optional[Tuple[float, Tuple[float, float, float], Tuple[float, float, float, float]]]:
        if not self._pose_history:
            return None
        # Naive nearest neighbor search; TODO: binary search in sorted list
        best = min(self._pose_history, key=lambda e: abs(e[0] - t))
        return best

    def destroy_node(self) -> None:  # type: ignore[override]
        try:
            if hasattr(self, "_csv_file") and self._csv_file:
                self._csv_file.close()
        finally:
            super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FusionLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

