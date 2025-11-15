MVP: Drone vSLAM + Wi‑Fi RSSI Fusion (Jetson)

Goal
- MVP for a drone-based system that uses pycuVSLAM for 3D visual SLAM (pose and optional map points) and logs Wi‑Fi RSSI, then fuses pose + RSSI into a log that can later be converted to a Wi‑Fi heatmap.

Packages
- slam_pycu_interface: wraps pycuVSLAM and publishes pose (and optional map points).
- wifi_monitor: polls Wi‑Fi RSSI and publishes readings.
- fusion_logger: subscribes to pose + RSSI and logs fused data to CSV.

Data Flow (text diagram)
- Camera -> slam_pycu_interface -> publishes /slam/pose (PoseStamped), optional /slam/map_points
- Wi‑Fi iface (wlan0) -> wifi_monitor -> publishes /wifi/rssi (String/JSON payload for now)
- fusion_logger subscribes to /slam/pose + /wifi/rssi -> writes logs/fused_log_*.csv

Structure
- config/
  - slam_config.yaml         # placeholder for pycuVSLAM + camera parameters
  - wifi_config.yaml         # Wi‑Fi interface + targets
- ros2_ws/
  - src/
    - slam_pycu_interface/
    - wifi_monitor/
    - fusion_logger/
- launch/
  - mvp_system.launch.py
- scripts/                   # helper scripts (TODO)
- logs/                      # output CSV logs

Setup (high-level, TODO details)
- Install ROS 2 (e.g., Humble/Irons), CUDA/cuDNN, and NVIDIA’s cuVSLAM + pycuVSLAM following NVIDIA docs. (TODO)
- Create a ROS 2 workspace and place these packages under ros2_ws/src.
- Build with colcon: `colcon build` (TODO: add package.xml/setup.py if needed).
- Configure camera driver and topic names to publish images (e.g., /camera/image_raw).
- Configure `config/slam_config.yaml` and `config/wifi_config.yaml` parameters.
- Launch: `ros2 launch mvp_system.launch.py` (adjust for your workspace and package installation).

Notes
- pycuVSLAM integration is stubbed with TODOs.
- Wi‑Fi polling is stubbed with TODOs.
- This repository is a starting skeleton, not a complete solution.
- The launch file assumes proper ROS 2 packaging/installation of nodes; see TODOs to adapt.

