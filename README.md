# MVP: Drone vSLAM + Wi‑Fi RSSI Fusion + Depth Estimation (Jetson)

## Goal
MVP for a drone-based system that:
1. Uses **stella_vslam** for visual SLAM (pose estimation and feature tracking)
2. Uses **Depth Anything V2** for monocular depth estimation and 3D reconstruction
3. Logs **Wi‑Fi RSSI** for signal strength mapping
4. Fuses pose + depth + RSSI into logs for Wi‑Fi heatmap generation

## Why Depth Anything V3?
- **Monocular depth estimation**: No need for stereo cameras
- **Robust**: Works in various environments (indoor/outdoor)
- **Real-time capable**: Optimized models available for edge devices
- **Open source**: MIT licensed
- **State-of-the-art**: Published by ByteDance in 2024

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Jetson Drone                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Camera (Monocular)                                             │
│       │                                                          │
│       ├──────────────────────────────────────┐                 │
│       │                                       │                 │
│       v                                       v                 │
│  ┌─────────────────┐              ┌──────────────────────┐    │
│  │ stella_vslam    │              │ Depth Anything V3    │    │
│  │ (Pose + Map)    │              │ (Depth Estimation)   │    │
│  └────────┬────────┘              └──────────┬───────────┘    │
│           │                                   │                 │
│           │ /slam/pose                       │ /depth/image    │
│           │ /slam/map_points                 │ /depth/cloud    │
│           │                                   │                 │
│           v                                   v                 │
│  ┌────────────────────────────────────────────────────┐        │
│  │            3D Reconstruction Fusion                │        │
│  │     (Combines SLAM pose + depth for 3D map)       │        │
│  └──────────────────────┬─────────────────────────────┘        │
│                         │                                       │
│                         │ /reconstruction/points               │
│                         │                                       │
│  Wi-Fi Interface (wlan0)                                       │
│       │                                                         │
│       v                                                         │
│  ┌──────────────┐                                              │
│  │ wifi_monitor │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│         │ /wifi/rssi                                           │
│         │                                                       │
│         v                                                       │
│  ┌─────────────────────────────────────┐                      │
│  │       Fusion Logger                  │                      │
│  │  (Pose + Depth + RSSI -> CSV/DB)    │                      │
│  └─────────────────┬────────────────────┘                      │
│                    │                                            │
│                    v                                            │
│         logs/fused_data_*.csv                                  │
│         logs/point_cloud_*.ply                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Packages

### 1. **slam_stella_interface** (replacing pycuVSLAM)
- Wraps stella_vslam for ROS 2
- Publishes:
  - `/slam/pose` (PoseStamped) - Camera pose in world frame
  - `/slam/map_points` (PointCloud2) - Sparse feature map
  - `/slam/tracking_status` (String) - TRACKING/LOST status

### 2. **depth_anything_node**
- Runs Depth Anything V3 model
- Subscribes to: `/camera/image_raw`
- Publishes:
  - `/depth/image` (Image) - Depth map visualization
  - `/depth/raw` (Image) - Raw depth values (32FC1)
  - `/depth/cloud` (PointCloud2) - 3D point cloud in camera frame

### 3. **reconstruction_fusion**
- Fuses SLAM pose + depth point clouds
- Subscribes to:
  - `/slam/pose`
  - `/depth/cloud`
- Publishes:
  - `/reconstruction/points` (PointCloud2) - Global 3D reconstruction
  - `/reconstruction/mesh` (optional) - Meshed surface
- Saves to disk: `logs/reconstruction_*.ply`

### 4. **wifi_monitor**
- Polls Wi‑Fi RSSI using system calls
- Publishes:
  - `/wifi/rssi` (WifiSignal custom msg) - RSSI readings with timestamp

### 5. **fusion_logger**
- Subscribes to:
  - `/slam/pose`
  - `/wifi/rssi`
  - `/reconstruction/points` (optional)
- Outputs:
  - `logs/fused_log_*.csv` - Time-synced pose + RSSI data
  - `logs/wifi_heatmap_*.json` - Processed for visualization

## Data Flow

```
Camera Stream
    │
    ├─→ stella_vslam ──→ Pose (x,y,z, qx,qy,qz,qw) ──┐
    │                                                  │
    └─→ Depth Anything V2 ──→ Depth Map ──────────────┤
                                                       │
                                                       v
                                             Reconstruction Fusion
                                                       │
                                                       v
                                              3D Point Cloud (Global Frame)
                                                       │
Wi-Fi Adapter (wlan0)                                 │
    │                                                  │
    v                                                  │
wifi_monitor ──→ RSSI readings ───────────────────────┤
                                                       │
                                                       v
                                                 Fusion Logger
                                                       │
                                                       v
                                      CSV: timestamp, x, y, z, quat, rssi, ...
                                      PLY: 3D reconstruction with colors
```

## Directory Structure

```
drone_wifi_slam/
├── README.md
├── config/
│   ├── slam_config.yaml          # stella_vslam configuration
│   ├── camera_config.yaml        # Camera calibration
│   ├── depth_config.yaml         # Depth Anything V2 settings
│   └── wifi_config.yaml          # Wi-Fi interface + targets
│
├── models/
│   ├── orb_vocab.fbow           # stella_vslam vocabulary
│   └── depth_anything_v2_vitl.pth  # Depth model weights
│
├── ros2_ws/
│   └── src/
│       ├── slam_stella_interface/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   ├── launch/
│       │   │   └── slam.launch.py
│       │   └── slam_stella_interface/
│       │       ├── __init__.py
│       │       ├── slam_node.py
│       │       └── stella_wrapper.py
│       │
│       ├── depth_anything_node/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   ├── launch/
│       │   │   └── depth.launch.py
│       │   └── depth_anything_node/
│       │       ├── __init__.py
│       │       ├── depth_node.py
│       │       └── depth_model.py
│       │
│       ├── reconstruction_fusion/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   └── reconstruction_fusion/
│       │       ├── __init__.py
│       │       ├── fusion_node.py
│       │       └── point_cloud_utils.py
│       │
│       ├── wifi_monitor/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   └── wifi_monitor/
│       │       ├── __init__.py
│       │       ├── wifi_node.py
│       │       └── rssi_scanner.py
│       │
│       └── fusion_logger/
│           ├── package.xml
│           ├── setup.py
│           └── fusion_logger/
│               ├── __init__.py
│               ├── logger_node.py
│               └── data_sync.py
│
├── launch/
│   └── mvp_system.launch.py     # Launch all nodes
│
├── scripts/
│   ├── download_models.sh       # Download Depth Anything V2 weights
│   ├── calibrate_camera.py      # Camera calibration helper
│   └── visualize_heatmap.py     # Post-processing visualization
│
├── logs/                         # Runtime data output
│   ├── fused_log_*.csv
│   ├── reconstruction_*.ply
│   └── wifi_heatmap_*.json
│
└── docs/
    ├── INSTALL.md               # Detailed installation guide
    ├── CALIBRATION.md           # Camera calibration instructions
    └── USAGE.md                 # How to run the system
```

## Setup Instructions

### Prerequisites
```bash
# 1. System dependencies
sudo apt update
sudo apt install -y \
    ros-humble-desktop \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    python3-opencv \
    python3-pip

# 2. Python dependencies
pip3 install \
    torch torchvision \
    opencv-python \
    numpy \
    pillow \
    pyyaml
```


# Download model weights
./scripts/download_models.sh

# Install Python package
pip3 install -e .
```

### Build ROS 2 Workspace
```bash
cd ~/drone_wifi_slam/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### Configure System
```bash
# 1. Calibrate camera
python3 scripts/calibrate_camera.py

# 2. Edit config files
nano config/slam_config.yaml
nano config/depth_config.yaml
nano config/wifi_config.yaml
```

## Running the System

### Launch Full System
```bash
cd ~/drone_wifi_slam/ros2_ws
source install/setup.bash
ros2 launch launch/mvp_system.launch.py
```

```

## Configuration Files

### slam_config.yaml
```yaml
slam:
  vocabulary_file: "../models/orb_vocab.fbow"
  camera_config: "../config/camera_config.yaml"
  frame_rate: 30
  
  publish:
    pose_topic: "/slam/pose"
    map_points_topic: "/slam/map_points"
    tracking_status_topic: "/slam/tracking_status"
```

### depth_config.yaml
```yaml
depth:
  model_path: "../models/depth_anything_v2_vitl.pth"
  encoder: "vitl"  # vitl, vitb, vits
  input_size: [518, 518]  # Height, Width
  
  camera_topic: "/camera/image_raw"
  
  publish:
    depth_image_topic: "/depth/image"
    depth_raw_topic: "/depth/raw"
    point_cloud_topic: "/depth/cloud"
  
  processing:
    use_gpu: true
    max_depth: 10.0  # meters
```

### wifi_config.yaml
```yaml
wifi:
  interface: "wlan0"
  scan_interval: 1.0  # seconds
  
  target_networks:
    - ssid: "DroneNet"
    - ssid: "TestAP"
  
  publish:
    rssi_topic: "/wifi/rssi"
```

## Output Data Format

### fused_log_*.csv
```csv
timestamp,x,y,z,qx,qy,qz,qw,rssi,ssid,bssid,frequency
1234567890.123,1.23,4.56,0.78,0.0,0.0,0.707,0.707,-45,DroneNet,AA:BB:CC:DD:EE:FF,5180
```

### reconstruction_*.ply (Point Cloud)
```
ply
format binary_little_endian 1.0
element vertex 100000
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
[binary data]
```

## Performance Targets (Jetson Orin)

| Component | Target FPS | GPU Util | Notes |
|-----------|-----------|----------|-------|
| Camera Input | 30 | - | USB/CSI camera |
| stella_vslam | 20-30 | 30% | Feature-based SLAM |
| Depth Anything V3 | 10-15 | 60% | ViT-Large model |
| Wi-Fi Scanning | 1 | <1% | Background polling |
| Data Logging | 30 | <5% | Buffered writes |

## TODO

- [ ] Implement stella_vslam ROS 2 wrapper
- [ ] Implement Depth Anything V2 ROS 2 node
- [ ] Implement 3D reconstruction fusion
- [ ] Implement Wi-Fi RSSI scanner
- [ ] Implement data logger with time synchronization
- [ ] Create launch files
- [ ] Add visualization tools
- [ ] Add camera calibration script
- [ ] Test full system integration
- [ ] Optimize for Jetson performance
- [ ] Add error handling and recovery
- [ ] Document API and usage

## References

- **stella_vslam**: https://github.com/stella-cv/stella_vslam
- **Depth Anything V3**: https://github.com/DepthAnything/Depth-Anything-V3
- **ROS 2 Humble**: https://docs.ros.org/en/humble/
- **Paper**: "Depth Anything V2" (arXiv:2406.09414)

## Notes

- This uses **stella_vslam** instead of cuVSLAM (no NVIDIA GPU dependency for SLAM)
- **Depth Anything V3** requires PyTorch and GPU for real-time performance
- Wi-Fi scanning requires appropriate permissions (`sudo` or `cap_net_raw` capability)
- Time synchronization between pose and RSSI is critical for accurate mapping
- Point cloud reconstruction can be memory-intensive; implement downsampling if needed
- Consider using **ROS 2 bags** for data collection and offline processing

## License

- stella_vslam: BSD-2-Clause
- Depth Anything V2: Apache 2.0
- This MVP code: MIT (your choice)