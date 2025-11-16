#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped # Or nav_msgs/Odometry

# --- PASTE YOUR PROTOTYPE CODE HERE ---
# Paste the get_signal_quality(), scan_wifi_iwlist(), etc.
# ...
import subprocess
import re
import csv
from datetime import datetime
# (All your other imports and functions...)
# ...
# --- END OF PASTED CODE ---


class HeatmapMapperNode(Node):

    def __init__(self):
        super().__init__('heatmap_mapper_node')
        
        # 1. Create a variable to store the latest pose
        self.last_known_pose = None
        self.data_log = [] # To store (x, y, z, rssi) tuples
        
        # 2. Create the subscriber for the VIO pose
        # (Change '/vio/pose' to your actual pose topic)
        self.pose_subscription = self.create_subscription(
            PoseStamped,      # Or Odometry
            '/vio/pose',      # <-- YOUR VIO TOPIC
            self.pose_callback,
            10) # QoS profile

        # 3. Create a timer that runs the scan function every 2 seconds
        self.scan_timer = self.create_timer(
            2.0,  # seconds
            self.scan_and_log_callback
        )
        
        self.get_logger().info("Heatmap Mapper Node has started.")
        self.get_logger().info("Subscribing to pose... Waiting for first pose message.")
        self.get_logger().info("Will scan WiFi every 2 seconds.")

    def pose_callback(self, msg):
        """
        This callback runs ~30 times/sec.
        It just saves the latest pose.
        """
        self.last_known_pose = msg.pose # Or msg.pose.pose if Odometry

    def scan_and_log_callback(self):
        """
        This callback runs every 2 seconds (from the timer).
        It's your main "fusing" logic.
        """
        if self.last_known_pose is None:
            self.get_logger().warn("Skipping scan, no pose data received yet.")
            return

        # --- 1. Get WiFi Data ---
        # Call the function from your prototype
        # We assume 'wlP1p1s0' is your interface
        self.get_logger().info("Running WiFi scan...")
        try:
            # NOTE: Your scan function *blocks* here for 1-2 seconds.
            # This is OK because it's in a timer callback and won't
            # block the 'pose_callback'.
            networks = scan_wifi_iwlist('wlP1p1s0') # Your function
        except Exception as e:
            self.get_logger().error(f"Scan failed: {e}")
            return
            
        self.get_logger().info(f"Scan complete. Found {len(networks)} networks.")

        # --- 2. Get Pose Data ---
        # We just grab the most recent pose we've saved
        current_pose = self.last_known_pose
        x = current_pose.position.x
        y = current_pose.position.y
        z = current_pose.position.z

        # --- 3. Fuse and Log Data ---
        # Loop through the networks and save the data
        # (This replaces your 'write_csv_output' logic)
        for net in networks:
            ssid = net.get('ssid', 'Unknown')
            rssi = net.get('rssi', -100)
            
            # Example: Only log the network you care about
            if ssid == "MyHomeNetwork": # <-- CHANGE THIS
                
                # We have the golden data point!
                log_entry = (x, y, z, rssi)
                self.get_logger().info(f"Logging data: {log_entry}")
                
                # Add to our internal list
                self.data_log.append(log_entry)
                
                # (Optional: write to file on every scan)
                self.write_to_csv(log_entry)


    def write_to_csv(self, log_entry):
        # You can move your CSV writing logic here
        # This is just a simple example
        file_path = 'heatmap_log.csv'
        try:
            with open(file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now()] + list(log_entry))
        except Exception as e:
            self.get_logger().error(f"Failed to write to CSV: {e}")


def main(args=None):
    rclpy.init(args=args)
    
    heatmap_node = HeatmapMapperNode()
    
    try:
        rclpy.spin(heatmap_node)
    except KeyboardInterrupt:
        pass
    finally:
        # Before shutting down, you could save all data
        heatmap_node.get_logger().info("Shutting down and saving final data...")
        # (e.g., call a final save function)
        heatmap_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()