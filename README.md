# AirSniff - WiFi RF Heatmap System

Drone-based WiFi RF heatmap using NVIDIA Jetson, Isaac ROS (pycuVSLAM), and WiFi RSSI monitoring.

## Quick Start

```bash
# 1. Setup virtual environment
./setup_venv.sh

# 2. Activate environment
source venv/bin/activate

# 3. Install system dependencies (Jetson/Ubuntu)
sudo apt install -y wireless-tools iw aircrack-ng ros-humble-rclpy ros-humble-std-msgs

# 4. Start developing (see TODO.md for implementation roadmap)
```

## Project Overview

**MVP Goal:** Drone-based system that fuses 3D visual SLAM with WiFi RSSI data to generate RF heatmaps.

### System Components

1. **slam_pycu_interface** - NVIDIA cuVSLAM wrapper
   - Publishes: `/slam/pose` (PoseStamped)
   - Optional: `/slam/map_points`

2. **wifi_monitor** - WiFi RSSI scanner **← YOUR COMPONENT**
   - Publishes: `/wifi/rssi` (JSON/custom message)
   - Captures 802.11 frames in monitor mode
   - Extracts RSSI from RadioTap headers

3. **fusion_logger** - Data fusion and logging
   - Subscribes: `/slam/pose` + `/wifi/rssi`
   - Outputs: `logs/fused_log_*.csv`

### Data Flow

```
Camera (CSI/USB)
    ↓
slam_pycu_interface → /slam/pose (position + orientation)
    ↓
WiFi Adapter (monitor mode)
    ↓
wifi_monitor → /wifi/rssi (BSSID, SSID, signal strength)
    ↓
fusion_logger → logs/fused_log_*.csv (timestamped pose + RSSI)
    ↓
Post-processing → WiFi RF Heatmap
```

## Requirements

### Hardware
- NVIDIA Jetson (Nano/Xavier NX/Orin)
- WiFi adapter with monitor mode support
- Camera (CSI or USB)
- Drone platform (optional for testing)

### Software
- Ubuntu 20.04/22.04
- ROS 2 Humble
- Python 3.8+
- JetPack 5.x/6.x (for Jetson)

## Installation

### Step 1: Virtual Environment

```bash
./setup_venv.sh
```

**Choose installation level:**
- **Minimal** (~50 MB) - Core WiFi monitoring only
- **Standard** (~300 MB) - WiFi + visualization [Recommended]
- **Full** (~500 MB) - Everything including dev tools

This installs Python packages from `requirements.txt` based on your selection.

### Step 2: System Dependencies

```bash
# On Jetson/Ubuntu
sudo apt update
sudo apt install -y \
  wireless-tools \
  iw \
  aircrack-ng \
  ros-humble-rclpy \
  ros-humble-std-msgs
```

### Step 3: NVIDIA cuVSLAM (SLAM developers)

Follow official installation guide:
https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam

## Project Structure

```
AirSniff/
├── README.md                # Project overview (this file)
├── SETUP_INSTRUCTIONS.md    # Detailed setup and troubleshooting
├── TODO.md                  # Complete implementation roadmap
├── requirements.txt         # Python dependencies (PRIMARY FILE)
│
├── setup_venv.sh            # Automated virtual environment setup
├── activate_venv.sh         # Quick venv activation
├── .gitignore              # Git ignore rules
│
├── config/
│   ├── slam_config.yaml    # pycuVSLAM parameters
│   └── wifi_config.yaml    # WiFi interface + scanning config
│
├── ros2_ws/
│   └── src/
│       ├── slam_pycu_interface/    # SLAM package
│       ├── wifi_monitor/           # WiFi package (YOUR WORK)
│       └── fusion_logger/          # Fusion package
│
├── launch/
│   └── mvp_system.launch.py       # System launch file
│
└── logs/                           # Output CSV logs
```

## Development Workflow

### Daily Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Build ROS2 workspace
cd ros2_ws
colcon build

# Source workspace
source install/setup.bash

# Run system
ros2 launch launch/mvp_system.launch.py
```

### WiFi Monitor Development (Your Component)

See **TODO.md** for complete 11-phase implementation roadmap.

**Quick overview:**
1. Create ROS2 package: `ros2_ws/src/wifi_monitor/`
2. Implement 802.11 packet capture in monitor mode
3. Parse RSSI from RadioTap headers
4. Create ROS2 publisher node
5. Publish to `/wifi/rssi` topic
6. Integration testing with SLAM

## Team Roles

| Role | Package | Responsibility | Topics |
|------|---------|---------------|--------|
| **WiFi Developer** | wifi_monitor | WiFi RSSI collection | Publishes `/wifi/rssi` |
| **SLAM Developer** | slam_pycu_interface | Visual SLAM, pose estimation | Publishes `/slam/pose` |
| **Fusion Developer** | fusion_logger | Data fusion, logging | Subscribes to both topics |

## Documentation

- **README.md** - Project overview (this file)
- **SETUP_INSTRUCTIONS.md** - Detailed setup, troubleshooting
- **TODO.md** - Complete implementation roadmap (11 phases, 550+ tasks)
- **requirements.txt** - Python dependencies with inline documentation

## Key Technical Details

### WiFi Monitoring
- **Mode**: Monitor mode (passive scanning)
- **Frames**: 802.11 beacon frames and probe responses
- **RSSI Source**: RadioTap headers (`dBm_AntSignal`)
- **Libraries**: Scapy for packet capture, pandas for aggregation
- **Output**: JSON or custom ROS2 message with BSSID, SSID, RSSI, channel

### SLAM Integration
- **Framework**: NVIDIA cuVSLAM (GPU-accelerated)
- **Output**: 6-DOF pose (position + orientation)
- **Coordinate System**: Shared with WiFi data via ROS2 transforms

### Data Fusion
- **Synchronization**: ROS2 message timestamps
- **Output Format**: CSV with columns: timestamp, x, y, z, roll, pitch, yaw, bssid, ssid, rssi
- **Post-processing**: Interpolation, heatmap generation (see TODO.md Phase 10)

## Getting Help

1. **Setup issues**: See `SETUP_INSTRUCTIONS.md`
2. **Implementation questions**: See `TODO.md` (searchable, comprehensive)
3. **Package documentation**: See inline comments in `requirements.txt`
4. **ROS2 issues**: Check ROS2 Humble documentation
5. **WiFi adapter issues**: See `TODO.md` Phase 3.4 "Error Handling & Permissions"

## Contributing

1. Follow the implementation plan in `TODO.md`
2. Use virtual environment for all development
3. Follow code style: black, pylint (included in dev dependencies)
4. Write unit tests for your components
5. Update documentation as needed
6. Test on Jetson before committing

## Notes

- This is an MVP (Minimum Viable Product) skeleton
- WiFi monitoring and SLAM integration are stubbed with TODOs
- See `TODO.md` for complete implementation checklist
- Each component can be developed independently via ROS2 topics

## License

[Add your license here]
