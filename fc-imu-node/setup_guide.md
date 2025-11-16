# Flight Controller IMU Node Setup Guide

This ROS 2 node reads IMU data from a flight controller (e.g., CubeOrange+) via MAVLink and publishes it to the `imu/data_raw` topic in ROS 2 format.

## Prerequisites

1. **ROS 2** (Humble or later) installed and sourced
2. **Python 3** (3.8+)
3. **pymavlink** installed:
   ```bash
   pip install pymavlink
   ```
   Or via apt (if available):
   ```bash
   sudo apt install python3-pymavlink
   ```

4. **Flight Controller** connected via USB/serial and running ArduPilot or PX4 firmware

## Hardware Setup

1. Connect your flight controller to the computer via USB
2. Identify the serial port:
   ```bash
   ls -la /dev/serial/by-id/
   ```
   Look for a device like: `usb-CubePilot_CubeOrange+_*`

## Configuration

The node uses ROS 2 parameters for configuration. You can set them via:

1. **Command line arguments:**
   ```bash
   ros2 run fc_imu_node fc_imu_node --ros-args \
     -p port:=/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00 \
     -p baud:=115200 \
     -p frame_id:=imu_link \
     -p publish_rate:=50.0 \
     -p data_stream_rate:=50
   ```

2. **Launch file** (recommended):
   ```python
   from launch import LaunchDescription
   from launch_ros.actions import Node

   def generate_launch_description():
       return LaunchDescription([
           Node(
               package='fc_imu_node',
               executable='fc_imu_node.py',
               name='fc_imu_node',
               parameters=[{
                   'port': '/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00',
                   'baud': 115200,
                   'frame_id': 'imu_link',
                   'publish_rate': 50.0,
                   'data_stream_rate': 50
               }]
           )
       ])
   ```

## Parameters

- **port** (string, default: `/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00`)
  - Serial port path to the flight controller

- **baud** (int, default: `115200`)
  - Serial baud rate

- **frame_id** (string, default: `imu_link`)
  - Frame ID for the IMU messages (used in TF)

- **publish_rate** (double, default: `50.0`)
  - ROS 2 publish rate in Hz

- **data_stream_rate** (int, default: `50`)
  - MAVLink data stream rate in Hz (requested from FC)

## Running the Node

### Direct execution:
```bash
python3 fc_imu_node.py
```

### As a ROS 2 node:
```bash
ros2 run fc_imu_node fc_imu_node
```

### With custom parameters:
```bash
ros2 run fc_imu_node fc_imu_node --ros-args -p port:=/dev/ttyUSB0 -p baud:=57600
```

## Verification

1. **Check that the node is running:**
   ```bash
   ros2 node list
   ```
   You should see `fc_imu_node`

2. **Check the topic:**
   ```bash
   ros2 topic list
   ```
   You should see `/imu/data_raw`

3. **Monitor IMU data:**
   ```bash
   ros2 topic echo /imu/data_raw
   ```

4. **Check publication rate:**
   ```bash
   ros2 topic hz /imu/data_raw
   ```

## Output Format

The node publishes `sensor_msgs/Imu` messages with:
- **linear_acceleration**: Acceleration in m/s² (x, y, z)
- **angular_velocity**: Angular velocity in rad/s (x, y, z)
- **header.frame_id**: Set from the `frame_id` parameter
- **header.stamp**: Current ROS 2 time

Note: Orientation and covariance fields are left as zeros (not provided by RAW_IMU message).

## Troubleshooting

### "No heartbeat received"
- Check that the flight controller is powered and connected
- Verify the port path is correct
- Check permissions: `sudo chmod 666 /dev/serial/by-id/...`
- Try a different baud rate (common: 115200, 57600, 38400)

### "No RAW_IMU received (timeout)"
- The FC may not be sending RAW_IMU messages
- Check ArduPilot/PX4 parameters for sensor data stream settings
- Try increasing the timeout or data_stream_rate parameter

### Permission denied
- Add your user to the dialout group:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  Then log out and back in.

### Import errors
- Ensure ROS 2 is sourced: `source /opt/ros/humble/setup.bash`
- Install pymavlink: `pip install pymavlink`

## Integration with VIO

This node publishes to the same topic (`imu/data_raw`) that the ESP32 IMU node was using, so it should be a drop-in replacement for VIO systems expecting IMU data at that topic.

### Integration Chain

The complete data flow is:
1. **fc_imu_node** → publishes `sensor_msgs/Imu` to `/imu/data_raw`
2. **VIO System** → subscribes to `/imu/data_raw` (and camera topics)
3. **VIO System** → publishes pose to `/vio/pose`
4. **Data Fuser (heatmap_mapper_node)** → subscribes to `/vio/pose`

### Topic Verification

To verify the integration:
```bash
# Check that IMU data is being published
ros2 topic echo /imu/data_raw

# Check the publication rate
ros2 topic hz /imu/data_raw

# Verify the VIO system can see it
ros2 topic list | grep imu
```

### Rate Considerations

- **Default publish rate**: 200 Hz (matches ESP32 node for VIO compatibility)
- **MAVLink stream rate**: 50 Hz (typical maximum for RAW_IMU messages)
- The node will republish the latest IMU data at 200 Hz, which is acceptable for VIO systems that can handle duplicate messages or interpolate

If your flight controller supports higher MAVLink rates, you can increase `data_stream_rate` parameter accordingly.

