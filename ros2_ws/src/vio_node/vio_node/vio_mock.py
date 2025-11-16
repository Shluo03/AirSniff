#!/usr/bin/env python3
"""
Mock VIO Node - Simulates position data for testing without hardware
Publishes fake pose data to /vio/pose for testing the fusion pipeline
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import numpy as np
import math


def euler_to_quaternion(roll, pitch, yaw):
    """Convert Euler angles to quaternion."""
    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)
    
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    
    return np.array([x, y, z, w])


class MockVIONode(Node):
    def __init__(self):
        super().__init__('mock_vio_node')
        
        # Declare parameters
        self.declare_parameter('publish_rate', 30.0)  # Hz
        self.declare_parameter('motion_pattern', 'square')  # square, circle, line, hover
        self.declare_parameter('motion_speed', 0.5)  # meters per second
        self.declare_parameter('motion_scale', 5.0)  # size of pattern in meters
        self.declare_parameter('start_x', 0.0)
        self.declare_parameter('start_y', 0.0)
        self.declare_parameter('start_z', 1.5)  # typical drone height
        
        # Get parameters
        self.publish_rate = self.get_parameter('publish_rate').value
        self.motion_pattern = self.get_parameter('motion_pattern').value
        self.motion_speed = self.get_parameter('motion_speed').value
        self.motion_scale = self.get_parameter('motion_scale').value
        self.start_x = self.get_parameter('start_x').value
        self.start_y = self.get_parameter('start_y').value
        self.start_z = self.get_parameter('start_z').value
        
        # Create publisher
        self.publisher_ = self.create_publisher(PoseStamped, '/vio/pose', 10)
        
        # Create timer
        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.publish_pose)
        
        # Motion state
        self.time_elapsed = 0.0
        self.frame_count = 0
        
        self.get_logger().info('Mock VIO Node Started')
        self.get_logger().info(f'Motion Pattern: {self.motion_pattern}')
        self.get_logger().info(f'Publish Rate: {self.publish_rate} Hz')
        self.get_logger().info(f'Motion Speed: {self.motion_speed} m/s')
        self.get_logger().info(f'Motion Scale: {self.motion_scale} m')
        self.get_logger().info(f'Start Position: ({self.start_x:.1f}, {self.start_y:.1f}, {self.start_z:.1f})')
    
    def get_position_for_pattern(self, t):
        """Calculate position based on motion pattern and time."""
        
        if self.motion_pattern == 'hover':
            # Stationary with small random drift
            noise = 0.01
            x = self.start_x + np.random.uniform(-noise, noise)
            y = self.start_y + np.random.uniform(-noise, noise)
            z = self.start_z + np.random.uniform(-noise, noise)
            yaw = 0.0
        
        elif self.motion_pattern == 'line':
            # Move in a straight line (forward along x-axis)
            distance = self.motion_speed * t
            x = self.start_x + distance
            y = self.start_y
            z = self.start_z
            yaw = 0.0  # facing forward
        
        elif self.motion_pattern == 'circle':
            # Move in a circle
            angular_speed = self.motion_speed / self.motion_scale
            angle = angular_speed * t
            x = self.start_x + self.motion_scale * np.cos(angle)
            y = self.start_y + self.motion_scale * np.sin(angle)
            z = self.start_z
            yaw = angle + np.pi/2  # tangent to circle
        
        elif self.motion_pattern == 'square':
            # Move in a square pattern
            perimeter = 4 * self.motion_scale
            distance = (self.motion_speed * t) % perimeter
            
            if distance < self.motion_scale:
                # Side 1: Move forward (positive x)
                x = self.start_x + distance
                y = self.start_y
                yaw = 0.0
            elif distance < 2 * self.motion_scale:
                # Side 2: Move right (positive y)
                x = self.start_x + self.motion_scale
                y = self.start_y + (distance - self.motion_scale)
                yaw = np.pi/2
            elif distance < 3 * self.motion_scale:
                # Side 3: Move backward (negative x)
                x = self.start_x + self.motion_scale - (distance - 2 * self.motion_scale)
                y = self.start_y + self.motion_scale
                yaw = np.pi
            else:
                # Side 4: Move left (negative y)
                x = self.start_x
                y = self.start_y + self.motion_scale - (distance - 3 * self.motion_scale)
                yaw = -np.pi/2
            
            z = self.start_z
        
        elif self.motion_pattern == 'figure8':
            # Move in a figure-8 pattern
            angular_speed = self.motion_speed / self.motion_scale
            angle = angular_speed * t
            x = self.start_x + self.motion_scale * np.sin(angle)
            y = self.start_y + self.motion_scale * np.sin(2 * angle) / 2
            z = self.start_z
            yaw = angle
        
        else:
            # Default: hover
            x = self.start_x
            y = self.start_y
            z = self.start_z
            yaw = 0.0
        
        return x, y, z, yaw
    
    def publish_pose(self):
        """Timer callback - publish pose."""
        self.frame_count += 1
        dt = 1.0 / self.publish_rate
        self.time_elapsed += dt
        
        # Get position for current time
        x, y, z, yaw = self.get_position_for_pattern(self.time_elapsed)
        
        # Create pose message
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'world'
        
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.position.z = float(z)
        
        # Convert yaw to quaternion (assuming level flight: roll=0, pitch=0)
        quat = euler_to_quaternion(0.0, 0.0, yaw)
        msg.pose.orientation.x = float(quat[0])
        msg.pose.orientation.y = float(quat[1])
        msg.pose.orientation.z = float(quat[2])
        msg.pose.orientation.w = float(quat[3])
        
        # Publish
        self.publisher_.publish(msg)
        
        # Log occasionally
        if self.frame_count % 300 == 0:  # Every 10 seconds at 30Hz
            self.get_logger().info(
                f'Frame {self.frame_count} | '
                f'Time: {self.time_elapsed:.1f}s | '
                f'Pos: ({x:.2f}, {y:.2f}, {z:.2f}) | '
                f'Yaw: {math.degrees(yaw):.1f}°'
            )
    
    def destroy_node(self):
        """Cleanup on shutdown."""
        self.get_logger().info(f'Mock VIO Node shutting down after {self.frame_count} frames')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = MockVIONode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

