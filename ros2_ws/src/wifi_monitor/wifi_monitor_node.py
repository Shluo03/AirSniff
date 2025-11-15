# File: ros2_ws/src/wifi_monitor/wifi_monitor_node.py

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import yaml


class WifiMonitor:
    """Encapsulates platform-specific Wi‑Fi polling (stub).

    TODOs:
    - Implement polling via `iw`, `nmcli`, or a Python Wi‑Fi library.
    - Parse RSSI (dBm), SSID, BSSID, channel/frequency, etc.
    - Filter by target SSIDs/BSSIDs when provided.
    """

    def __init__(self, interface: str) -> None:
        self.interface = interface

    def poll_wifi(self) -> List[Dict[str, Any]]:
        """Poll Wi‑Fi environment and return a list of dicts.

        Returns:
            List[Dict[str, Any]]: Each entry may contain keys like:
                {
                  "timestamp": float,
                  "ssid": str,
                  "bssid": str,
                  "rssi_dbm": int,
                  "channel": int,
                }

        This is a stub and returns an empty list for now.
        """
        # TODO: Use subprocess to invoke 'iw dev <iface> link/scan' or 'nmcli -f ...'
        # TODO: Parse outputs and populate structured readings.
        return []


class WifiMonitorNode(Node):
    """ROS2 node that periodically polls Wi‑Fi RSSI and publishes readings.

    Publishes on topic /wifi/rssi as a JSON-encoded String (placeholder).
    TODO: define and use a custom message type for structured Wi‑Fi readings.
    """

    def __init__(self) -> None:
        super().__init__("wifi_monitor")

        # Parameters
        self.declare_parameter("config_path", "config/wifi_config.yaml")
        cfg_path = self.get_parameter("config_path").get_parameter_value().string_value
        self._config = self._load_config(cfg_path)

        iface = self._config.get("interface", "wlan0")
        self._poll_interval = float(self._config.get("poll_interval_sec", 1.0))
        self._targets = self._config.get("targets", {})

        self._monitor = WifiMonitor(interface=iface)

        self._pub = self.create_publisher(String, "/wifi/rssi", 10)
        self._timer = self.create_timer(self._poll_interval, self._on_timer)

        self.get_logger().info(f"wifi_monitor initialized on iface={iface} interval={self._poll_interval}s")

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            self.get_logger().warn(f"wifi config not found at {path}, using defaults")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.get_logger().error(f"failed to load wifi config: {e}")
            return {}

    def _on_timer(self) -> None:
        readings = self._monitor.poll_wifi()
        now = time.time()
        for r in readings:
            r = dict(r)
            r.setdefault("timestamp", now)

            # Optional filter by targets (placeholder)
            ssids = set(self._targets.get("ssids", []) or [])
            bssids = set(self._targets.get("bssids", []) or [])
            if ssids and r.get("ssid") not in ssids:
                continue
            if bssids and r.get("bssid") not in bssids:
                continue

            msg = String()
            msg.data = json.dumps(r)
            self._pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WifiMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

