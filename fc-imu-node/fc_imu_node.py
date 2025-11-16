#!/usr/bin/env python3
"""
ROS 2 IMU Node for Flight Controller
Reads IMU data from a flight controller via MAVLink and publishes to ROS 2.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from pymavlink import mavutil
import threading
import time


class FCImuNode(Node):
    """ROS 2 node that reads IMU data from flight controller via MAVLink."""

    def __init__(self):
        super().__init__('fc_imu_node')
        
        # Declare ROS parameters
        self.declare_parameter('port', '/dev/serial/by-id/usb-CubePilot_CubeOrange+_250048000D51333233343437-if00')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('publish_rate', 200.0)  # Hz (matches ESP32 node rate for VIO)
        self.declare_parameter('data_stream_rate', 50)  # Hz for MAVLink stream (FC may limit this)
        
        # Get parameters
        self.port = self.get_parameter('port').get_parameter_value().string_value
        self.baud = self.get_parameter('baud').get_parameter_value().integer_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.publish_rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        self.data_stream_rate = self.get_parameter('data_stream_rate').get_parameter_value().integer_value
        
        # MAVLink connection
        self.master = None
        self.running = False
        self.imu_thread = None
        
        # Latest IMU data (thread-safe)
        self.latest_imu_data = None
        self.imu_lock = threading.Lock()
        
        # Create publisher
        self.imu_publisher = self.create_publisher(
            Imu,
            '/imu/data_raw',  # Same topic as ESP32 node (absolute path for global topic)
            10
        )
        
        # Create timer for publishing
        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.publish_imu_callback)
        
        self.get_logger().info(f'FC IMU Node initialized')
        self.get_logger().info(f'  Port: {self.port}')
        self.get_logger().info(f'  Baud: {self.baud}')
        self.get_logger().info(f'  Frame ID: {self.frame_id}')
        self.get_logger().info(f'  Publish rate: {self.publish_rate} Hz')
        
        # Start MAVLink connection in a separate thread
        self.start_mavlink_connection()
    
    def start_mavlink_connection(self):
        """Start the MAVLink connection in a background thread."""
        self.running = True
        self.imu_thread = threading.Thread(target=self._mavlink_read_loop, daemon=True)
        self.imu_thread.start()
        self.get_logger().info('MAVLink connection thread started')
    
    def _mavlink_read_loop(self):
        """Background thread that reads MAVLink messages."""
        try:
            self.get_logger().info(f'Connecting to flight controller at {self.port}...')
            self.master = mavutil.mavlink_connection(self.port, baud=self.baud)
            
            self.get_logger().info('Waiting for heartbeat...')
            self.master.wait_heartbeat()
            self.get_logger().info(
                f'Heartbeat received from system {self.master.target_system}, '
                f'component {self.master.target_component}'
            )
            
            # Request RAW_IMU data stream
            self.master.mav.request_data_stream_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,
                self.data_stream_rate,  # rate in Hz
                1  # start
            )
            self.get_logger().info(f'Requested RAW_IMU stream at {self.data_stream_rate} Hz')
            
            # Read loop
            while self.running:
                msg = self.master.recv_match(type="RAW_IMU", blocking=True, timeout=2)
                if msg is None:
                    self.get_logger().warn('No RAW_IMU received (timeout)')
                    continue
                
                # Extract raw values
                # MAVLink RAW_IMU: accelerometer in milli-g, gyro in milli-rad/s
                accel_x = msg.xacc  # milli-g
                accel_y = msg.yacc  # milli-g
                accel_z = msg.zacc  # milli-g
                gyro_x = msg.xgyro  # milli-rad/s
                gyro_y = msg.ygyro  # milli-rad/s
                gyro_z = msg.zgyro  # milli-rad/s
                
                # Convert to SI units
                # Accelerometer: milli-g -> m/s² (1 g = 9.80665 m/s²)
                # Gyro: milli-rad/s -> rad/s
                G_TO_M_S2 = 9.80665
                accel_m_s2 = [
                    accel_x * 0.001 * G_TO_M_S2,
                    accel_y * 0.001 * G_TO_M_S2,
                    accel_z * 0.001 * G_TO_M_S2
                ]
                gyro_rad_s = [
                    gyro_x * 0.001,
                    gyro_y * 0.001,
                    gyro_z * 0.001
                ]
                
                # Store latest data (thread-safe)
                with self.imu_lock:
                    self.latest_imu_data = {
                        'timestamp': time.time(),
                        'accel': accel_m_s2,
                        'gyro': gyro_rad_s
                    }
        
        except Exception as e:
            self.get_logger().error(f'MAVLink error: {e}')
            self.running = False
    
    def publish_imu_callback(self):
        """Timer callback that publishes the latest IMU data."""
        with self.imu_lock:
            if self.latest_imu_data is None:
                return
            
            imu_data = self.latest_imu_data
        
        # Create ROS 2 Imu message
        imu_msg = Imu()
        
        # Set header
        now = self.get_clock().now()
        imu_msg.header.stamp = now.to_msg()
        imu_msg.header.frame_id = self.frame_id
        
        # Set linear acceleration (m/s²)
        imu_msg.linear_acceleration.x = float(imu_data['accel'][0])
        imu_msg.linear_acceleration.y = float(imu_data['accel'][1])
        imu_msg.linear_acceleration.z = float(imu_data['accel'][2])
        
        # Set angular velocity (rad/s)
        imu_msg.angular_velocity.x = float(imu_data['gyro'][0])
        imu_msg.angular_velocity.y = float(imu_data['gyro'][1])
        imu_msg.angular_velocity.z = float(imu_data['gyro'][2])
        
        # Note: Orientation and covariance are left as zeros
        # These would need to be computed from integration or provided by the FC
        
        # Publish
        self.imu_publisher.publish(imu_msg)
    
    def destroy_node(self):
        """Cleanup on shutdown."""
        self.get_logger().info('Shutting down FC IMU node...')
        self.running = False
        if self.imu_thread:
            self.imu_thread.join(timeout=2)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    fc_imu_node = FCImuNode()
    
    try:
        rclpy.spin(fc_imu_node)
    except KeyboardInterrupt:
        pass
    finally:
        fc_imu_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

