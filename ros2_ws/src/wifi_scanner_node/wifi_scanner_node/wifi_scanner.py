#!/usr/bin/env python3
"""
WiFi Scanner ROS2 Node
Publishes WiFi RSSI data to /wifi/rssi topic
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess
import re
import json
import time
from datetime import datetime

class WiFiScannerNode(Node):
    def __init__(self):
        super().__init__('wifi_scanner_node')
        
        self.declare_parameter('interface', 'wlP1p1s0')
        self.declare_parameter('scan_method', 'iwlist')  # 'iwlist' or 'nmcli'
        self.declare_parameter('scan_interval', 2.0)  # seconds
        self.declare_parameter('min_rssi', -90)
        self.declare_parameter('max_rssi', -20)
        self.declare_parameter('target_ssid', '')  # Target SSID to track (empty = all networks)
        
        self.interface = self.get_parameter('interface').value
        self.scan_method = self.get_parameter('scan_method').value
        self.scan_interval = self.get_parameter('scan_interval').value
        self.min_rssi = self.get_parameter('min_rssi').value
        self.max_rssi = self.get_parameter('max_rssi').value
        self.target_ssid = self.get_parameter('target_ssid').value
        
        self.publisher_ = self.create_publisher(String, '/wifi/rssi', 10)
        
        self.timer = self.create_timer(self.scan_interval, self.scan_callback)
        
        self.scan_count = 0
        
        self.get_logger().info('WiFi Scanner Node Started')
        self.get_logger().info(f'Interface: {self.interface}')
        self.get_logger().info(f'Scan Method: {self.scan_method}')
        self.get_logger().info(f'Scan Interval: {self.scan_interval}s')
        self.get_logger().info(f'RSSI Range: {self.min_rssi} to {self.max_rssi} dBm')
        if self.target_ssid:
            self.get_logger().info(f'Target SSID: "{self.target_ssid}" (single network mode)')
        else:
            self.get_logger().info('Target SSID: ALL (scanning all networks)')
    
    def get_signal_quality(self, rssi):
        """Convert RSSI to human-readable quality."""
        if rssi >= -50:
            return "Excellent"
        elif rssi >= -60:
            return "Good"
        elif rssi >= -70:
            return "Fair"
        elif rssi >= -80:
            return "Weak"
        else:
            return "Very Weak"
    
    def scan_wifi_iwlist(self):
        """Scan WiFi networks using iwlist."""
        try:
            result = subprocess.run(
                ['sudo', 'iwlist', self.interface, 'scan'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.get_logger().error(f'iwlist error: {result.stderr}')
                return []
            
            networks = []
            current_network = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                if 'Cell' in line and 'Address:' in line:
                    if current_network:
                        networks.append(current_network)
                    current_network = {}
                    match = re.search(r'Address: ([0-9A-Fa-f:]{17})', line)
                    if match:
                        current_network['bssid'] = match.group(1)
                
                elif 'ESSID:' in line:
                    match = re.search(r'ESSID:"([^"]*)"', line)
                    if match:
                        ssid = match.group(1)
                        current_network['ssid'] = ssid if ssid else '<Hidden Network>'
                
                elif 'Channel:' in line or 'Frequency:' in line:
                    match = re.search(r'Channel:?(\d+)', line)
                    if match:
                        current_network['channel'] = int(match.group(1))
                
                elif 'Signal level=' in line:
                    match = re.search(r'Signal level=(-?\d+)', line)
                    if match:
                        rssi = int(match.group(1))
                        if rssi > 0:
                            rssi = -100 + (rssi / 2)
                        current_network['rssi'] = int(rssi)
                        current_network['quality'] = self.get_signal_quality(rssi)
            
            if current_network:
                networks.append(current_network)
            
            return networks
            
        except subprocess.TimeoutExpired:
            self.get_logger().error('WiFi scan timeout')
            return []
        except Exception as e:
            self.get_logger().error(f'WiFi scan error: {e}')
            return []
    
    def scan_wifi_nmcli(self):
        """Scan WiFi networks using nmcli."""
        try:
            subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'],
                          capture_output=True, timeout=5)
            
            result = subprocess.run(
                ['nmcli', '-f', 'SSID,BSSID,CHAN,SIGNAL', 'dev', 'wifi', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return []
            
            networks = []
            lines = result.stdout.strip().split('\n')[1:]
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    ssid = parts[0] if parts[0] != '--' else '<Hidden Network>'
                    bssid = parts[1] if ':' in parts[1] else parts[2]
                    
                    signal = None
                    for part in reversed(parts):
                        if part.isdigit():
                            signal = int(part)
                            break
                    
                    if signal is not None:
                        rssi = -100 + (signal / 2)
                        networks.append({
                            'ssid': ssid,
                            'bssid': bssid,
                            'rssi': int(rssi),
                            'quality': self.get_signal_quality(rssi)
                        })
            
            return networks
            
        except Exception as e:
            self.get_logger().error(f'nmcli scan error: {e}')
            return []
    
    def filter_networks(self, networks):
        """Filter networks by RSSI range and optionally by target SSID."""
        filtered = []
        for net in networks:
            rssi = net.get('rssi', -100)
            ssid = net.get('ssid', '')
            
            # Check RSSI range
            if not (self.min_rssi <= rssi <= self.max_rssi):
                continue
            
            # Check target SSID if specified
            if self.target_ssid and ssid != self.target_ssid:
                continue
            
            filtered.append(net)
        
        return filtered
    
    def scan_callback(self):
        """Timer callback for periodic WiFi scanning."""
        self.scan_count += 1
        
        # Perform scan
        if self.scan_method == 'iwlist':
            networks = self.scan_wifi_iwlist()
        else:
            networks = self.scan_wifi_nmcli()
        
        # Filter networks
        networks = self.filter_networks(networks)
        
        # Create ROS message
        msg = String()
        msg_data = {
            'header': {
                'timestamp': self.get_clock().now().to_msg().sec + \
                            self.get_clock().now().to_msg().nanosec * 1e-9,
                'scan_number': self.scan_count,
                'frame_id': 'wifi_antenna'
            },
            'networks': networks
        }
        msg.data = json.dumps(msg_data)
        
        # Publish
        self.publisher_.publish(msg)
        
        self.get_logger().info(
            f'Scan #{self.scan_count}: Found {len(networks)} networks'
        )


def main(args=None):
    rclpy.init(args=args)
    
    node = WiFiScannerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('Shutting down WiFi Scanner Node')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

