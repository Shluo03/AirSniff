# Deployment Guide for Jetson

This guide explains how to deploy the `fc_imu_node` package to your Jetson device.

## Prerequisites on Jetson

1. **ROS 2 Humble** (or later) installed and sourced
2. **Python 3** (3.8+)
3. **pymavlink** installed:
   ```bash
   pip3 install pymavlink
   # OR
   sudo apt install python3-pymavlink
   ```

## Deployment Steps

### Option 1: Copy to ROS Workspace (Recommended)

1. **On your development machine**, ensure the package is ready:
   ```bash
   cd /path/to/AirSniff/fc-imu-node
   # Verify structure
   ls -la
   ```

2. **Transfer to Jetson**:
   ```bash
   # From your dev machine, copy to Jetson
   scp -r fc-imu-node user@jetson-ip:~/ros2_ws/src/
   
   # OR use git (if you've committed the changes)
   # On Jetson:
   cd ~/ros2_ws/src
   git clone <your-repo-url>
   cd AirSniff/fc-imu-node
   ```

3. **On Jetson**, build the package:
   ```bash
   cd ~/ros2_ws
   colcon build --packages-select fc_imu_node
   source install/setup.bash
   ```

4. **Verify installation**:
   ```bash
   ros2 pkg list | grep fc_imu_node
   ros2 run fc_imu_node fc_imu_node --help
   ```

### Option 2: Direct Copy (Quick Test)

If you just want to test without a full workspace:

1. **Copy the package**:
   ```bash
   scp -r fc-imu-node user@jetson-ip:~/
   ```

2. **On Jetson**, add to PYTHONPATH:
   ```bash
   export PYTHONPATH=$PYTHONPATH:~/fc-imu-node
   ```

3. **Run directly**:
   ```bash
   python3 ~/fc-imu-node/fc_imu_node/fc_imu_node.py
   ```

## Post-Deployment Setup

1. **Identify the flight controller port**:
   ```bash
   ls -la /dev/serial/by-id/
   ```

2. **Set permissions** (if needed):
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in for changes to take effect
   ```

3. **Test the node**:
   ```bash
   ros2 launch fc_imu_node fc_imu_node.launch.py \
     port:=/dev/serial/by-id/usb-CubePilot_CubeOrange+_YOUR_ID-if00
   ```

4. **Verify IMU data**:
   ```bash
   # In another terminal
   ros2 topic echo /imu/data_raw
   ros2 topic hz /imu/data_raw
   ```

## Integration with Master Launch

To integrate with your master launch file, add:

```python
from launch_ros.actions import Node

fc_imu_node = Node(
    package='fc_imu_node',
    executable='fc_imu_node',
    name='fc_imu_node',
    parameters=[{
        'port': '/dev/serial/by-id/usb-CubePilot_CubeOrange+_YOUR_ID-if00',
        'baud': 115200,
        'frame_id': 'imu_link',
        'publish_rate': 200.0,
        'data_stream_rate': 50
    }]
)
```

## Troubleshooting

- **"Package not found"**: Make sure you've built and sourced the workspace
- **"Permission denied"** on serial port: Add user to dialout group
- **"No heartbeat"**: Check FC connection and port path
- **"Import error"**: Install pymavlink: `pip3 install pymavlink`

