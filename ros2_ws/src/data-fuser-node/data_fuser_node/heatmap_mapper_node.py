#!/usr/bin/env python3
"""
Heatmap Mapper Node - Data Fusion for WiFi RSSI + VIO Pose
Subscribes to /vio/pose and /wifi/rssi, fuses data, logs to CSV
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
import json
import csv
import os
from datetime import datetime


class HeatmapMapperNode(Node):
    def __init__(self):
        super().__init__('heatmap_mapper_node')
        
        # Declare parameters
        self.declare_parameter('output_dir', 'logs')
        self.declare_parameter('output_file', 'fused_heatmap.csv')
        self.declare_parameter('target_ssid', '')  # Empty = log all networks
        self.declare_parameter('min_rssi', -90)
        
        # Get parameters
        self.output_dir = self.get_parameter('output_dir').value
        self.output_file = self.get_parameter('output_file').value
        self.target_ssid = self.get_parameter('target_ssid').value
        self.min_rssi = self.get_parameter('min_rssi').value
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        self.csv_path = os.path.join(self.output_dir, self.output_file)
        
        # State variables
        self.last_known_pose = None
        self.data_count = 0
        
        # Create subscribers
        self.pose_subscription = self.create_subscription(
            PoseStamped,
            '/vio/pose',
            self.pose_callback,
            10
        )
        
        self.wifi_subscription = self.create_subscription(
            String,
            '/wifi/rssi',
            self.wifi_callback,
            10
        )
        
        # Initialize CSV file
        self._init_csv()
        
        self.get_logger().info('Heatmap Mapper Node Started')
        self.get_logger().info(f'Output file: {self.csv_path}')
        self.get_logger().info(f'Target SSID: {self.target_ssid if self.target_ssid else "ALL"}')
        self.get_logger().info(f'Min RSSI: {self.min_rssi} dBm')
        self.get_logger().info('Waiting for pose and WiFi data...')
    
    def _init_csv(self):
        """Initialize CSV file with header."""
        file_exists = os.path.exists(self.csv_path)
        
        if not file_exists:
            try:
                with open(self.csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'timestamp',
                        'x', 'y', 'z',
                        'qx', 'qy', 'qz', 'qw',
                        'bssid', 'ssid', 'rssi', 'channel', 'quality'
                    ])
                self.get_logger().info(f'Created new CSV file: {self.csv_path}')
            except Exception as e:
                self.get_logger().error(f'Failed to create CSV file: {e}')
    
    def pose_callback(self, msg):
        """
        Callback for VIO pose updates.
        Runs at ~30Hz, just stores the latest pose.
        """
        self.last_known_pose = msg
    
    def wifi_callback(self, msg):
        """
        Callback for WiFi scan results.
        This is where the fusion happens!
        """
        # Check if we have pose data
        if self.last_known_pose is None:
            self.get_logger().warn('Skipping WiFi data - no pose received yet')
            return
        
        # Parse WiFi data (JSON format)
        try:
            wifi_data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Failed to parse WiFi data: {e}')
            return
        
        networks = wifi_data.get('networks', [])
        
        if not networks:
            self.get_logger().debug('No networks in WiFi scan')
            return
        
        # Get current pose
        pose = self.last_known_pose
        x = pose.pose.position.x
        y = pose.pose.position.y
        z = pose.pose.position.z
        qx = pose.pose.orientation.x
        qy = pose.pose.orientation.y
        qz = pose.pose.orientation.z
        qw = pose.pose.orientation.w
        
        # Fuse and log data
        logged_count = 0
        for net in networks:
            ssid = net.get('ssid', 'Unknown')
            bssid = net.get('bssid', 'Unknown')
            rssi = net.get('rssi', -100)
            channel = net.get('channel', 0)
            quality = net.get('quality', 'Unknown')
            
            # Filter by SSID if specified
            if self.target_ssid and ssid != self.target_ssid:
                continue
            
            # Filter by minimum RSSI
            if rssi < self.min_rssi:
                continue
            
            # Write to CSV
            self._write_csv_row(x, y, z, qx, qy, qz, qw, bssid, ssid, rssi, channel, quality)
            logged_count += 1
        
        if logged_count > 0:
            self.data_count += logged_count
            self.get_logger().info(
                f'Logged {logged_count} networks at pos({x:.2f}, {y:.2f}, {z:.2f}) | Total: {self.data_count}'
            )
    
    def _write_csv_row(self, x, y, z, qx, qy, qz, qw, bssid, ssid, rssi, channel, quality):
        """Write a single data point to CSV."""
        try:
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    f'{x:.6f}', f'{y:.6f}', f'{z:.6f}',
                    f'{qx:.6f}', f'{qy:.6f}', f'{qz:.6f}', f'{qw:.6f}',
                    bssid, ssid, rssi, channel, quality
                ])
        except Exception as e:
            self.get_logger().error(f'Failed to write CSV row: {e}')
    
    def destroy_node(self):
        """Cleanup on shutdown."""
        self.get_logger().info(f'Shutting down. Total data points logged: {self.data_count}')
        self.get_logger().info(f'Data saved to: {self.csv_path}')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = HeatmapMapperNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

