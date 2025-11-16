# FC IMU Node

ROS 2 node that reads IMU data from a flight controller (e.g., CubeOrange+) via MAVLink and publishes it to ROS 2 topics.

## Quick Start

### Building the Package

If this package is in a ROS 2 workspace:

```bash
cd ~/ros2_ws  # or your workspace directory
colcon build --packages-select fc_imu_node
source install/setup.bash
```

### Running the Node

**Using launch file (recommended):**
```bash
ros2 launch fc_imu_node fc_imu_node.launch.py
```

**With custom parameters:**
```bash
ros2 launch fc_imu_node fc_imu_node.launch.py \
  port:=/dev/ttyUSB0 \
  baud:=115200 \
  publish_rate:=200.0
```

**Direct execution:**
```bash
ros2 run fc_imu_node fc_imu_node
```

## Package Structure

```
fc-imu-node/
├── fc_imu_node/          # Python package
│   ├── __init__.py
│   └── fc_imu_node.py    # Main node implementation
├── launch/               # Launch files
│   └── fc_imu_node.launch.py
├── resource/             # Package resource marker
│   └── fc_imu_node
├── package.xml           # ROS 2 package manifest
├── setup.py              # Python package setup
├── setup.cfg              # Python package config
├── setup_guide.md         # Detailed setup instructions
└── README.md             # This file
```

## Dependencies

- ROS 2 (Humble or later)
- Python 3 (3.8+)
- pymavlink: `pip install pymavlink` or `sudo apt install python3-pymavlink`

## Topics

- **Publishes:** `/imu/data_raw` (sensor_msgs/Imu)

## Parameters

See `setup_guide.md` for detailed parameter documentation.

## Integration

This node is designed to be a drop-in replacement for the ESP32 IMU node. It publishes to the same topic (`/imu/data_raw`) that VIO systems expect.

For more details, see `setup_guide.md`.

