# File: offline/fuse_wifi_posthoc.py

"""
Post-hoc fusion of Wi‑Fi RSSI logs with reconstructed poses.

Inputs:
- Wi‑Fi CSV (timestamp, ssid, bssid, rssi_dbm, channel)
- Pose file (e.g., CSV/JSON with timestamp, x, y, z, qw, qx, qy, qz)

Output:
- Fused CSV: timestamp, x, y, z, qw, qx, qy, qz, ssid, bssid, rssi_dbm, channel

This is a skeleton script with TODOs.
"""

from __future__ import annotations

from typing import Optional


def fuse_wifi_with_poses(wifi_csv: str, poses_path: str, out_csv: str) -> Optional[str]:
    # TODO: implement nearest-neighbor matching by timestamp and write fused CSV
    return None


def main() -> None:
    # TODO: argparse for wifi_csv, poses_path, out_csv
    pass


if __name__ == "__main__":
    main()

