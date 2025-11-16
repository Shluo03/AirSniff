# File: ros2_ws/src/video_recorder/video_recorder_node.py

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSHistoryPolicy,
    QoSReliabilityPolicy,
    QoSDurabilityPolicy,
)
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class VideoRecorderNode(Node):
    """Records incoming images to MP4 and logs per-frame timestamps.

    Notes:
    - Uses OpenCV VideoWriter if available; otherwise runs without writing video.
    - Writes timestamps to JSON lines file beside the MP4.
    - Expects a single image stream; for stereo, use two recorders or extend this.
    """

    def __init__(self) -> None:
        super().__init__("video_recorder")

        # Parameters
        self.declare_parameter("output_dir", "logs/video")
        self.declare_parameter("base_name", "capture")
        self.declare_parameter("fps", 30.0)
        self.declare_parameter("topic", "/camera/image_raw")
        self.declare_parameter("encoding", "mp4v")  # fourcc

        self._out_dir = Path(self.get_parameter("output_dir").get_parameter_value().string_value)
        self._base = self.get_parameter("base_name").get_parameter_value().string_value
        self._fps = float(self.get_parameter("fps").get_parameter_value().double_value)
        self._topic = self.get_parameter("topic").get_parameter_value().string_value
        self._fourcc = self.get_parameter("encoding").get_parameter_value().string_value

        self._out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        self._mp4_path = self._out_dir / f"{self._base}_{ts}.mp4"
        self._ts_path = self._out_dir / f"{self._base}_{ts}_timestamps.jsonl"

        self._bridge = CvBridge()
        self._writer = None  # lazy init when first frame arrives
        self._ts_file = open(self._ts_path, "w", encoding="utf-8")
        self._frame_size = None  # (w, h)

        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self._sub = self.create_subscription(Image, self._topic, self._on_image, qos)

        self.get_logger().info(
            f"video_recorder: topic={self._topic} -> {self._mp4_path} (ts: {self._ts_path})"
        )

    def _open_writer(self, width: int, height: int) -> None:
        try:
            import cv2  # type: ignore
        except Exception as e:
            self.get_logger().warn(f"OpenCV not available; will not write video: {e}")
            self._writer = None
            return

        fourcc = cv2.VideoWriter_fourcc(*self._fourcc)
        self._writer = cv2.VideoWriter(str(self._mp4_path), fourcc, self._fps, (width, height), True)
        if not self._writer or not self._writer.isOpened():
            self.get_logger().error("Failed to open VideoWriter; check codec/fourcc and path")
            self._writer = None

    def _on_image(self, msg: Image) -> None:
        # Timestamp from message header (sec + nsec)
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        try:
            # Preserve color if possible, else convert to BGR8
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception:
            frame = self._bridge.imgmsg_to_cv2(msg)

        h, w = frame.shape[:2]
        if self._writer is None:
            self._frame_size = (w, h)
            self._open_writer(w, h)

        # Write frame if writer available
        if self._writer is not None:
            try:
                self._writer.write(frame)
            except Exception as e:
                self.get_logger().error(f"Video write failed: {e}")

        # Append timestamp record
        rec = {"timestamp": t, "frame_index": None, "width": w, "height": h}
        self._ts_file.write(json.dumps(rec) + "\n")

    def destroy_node(self) -> None:  # type: ignore[override]
        try:
            if self._writer is not None:
                try:
                    self._writer.release()
                except Exception:
                    pass
            if hasattr(self, "_ts_file") and self._ts_file:
                self._ts_file.flush()
                self._ts_file.close()
        finally:
            super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VideoRecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

