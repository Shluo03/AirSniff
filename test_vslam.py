#!/usr/bin/env python3
"""Simple test script for Isaac VSLAM node without needing ROS 2 colcon build.

This script directly tests the PycuVSLAMManager and mock frame processing.
"""

import sys
import time
from pathlib import Path

# Add the package to the path
package_path = Path(__file__).parent / "ros2_ws" / "src" / "slam_pycu_interface"
sys.path.insert(0, str(package_path))

from pycu_slam_wrapper import PycuVSLAMManager
import numpy as np


def generate_test_frame(frame_idx: int, width: int = 640, height: int = 480) -> np.ndarray:
    """Generate a simple test frame."""
    frame = np.zeros((height, width), dtype=np.uint8)
    
    # Add a moving circle
    x_center = width // 2 + int(10 * np.sin(frame_idx * 0.2))
    y_center = height // 2 + int(10 * np.cos(frame_idx * 0.2))
    
    y, x = np.ogrid[:height, :width]
    mask = (x - x_center) ** 2 + (y - y_center) ** 2 <= 50 ** 2
    frame[mask] = 200
    
    # Add noise
    noise = np.random.randint(0, 30, (height, width), dtype=np.uint8)
    frame = np.clip(frame.astype(int) + noise.astype(int), 0, 255).astype(np.uint8)
    
    return frame


def main():
    print("Isaac VSLAM Test - Processing Frames and Printing Position Data")
    print("=" * 60)
    
    # Initialize the SLAM manager
    config_path = Path(__file__).parent / "config" / "slam_config.yaml"
    manager = PycuVSLAMManager(config_path=str(config_path))
    manager.initialize_slam()
    
    print(f"SLAM Manager initialized with config: {config_path}")
    print("=" * 60)
    
    # Process some test frames
    num_frames = 60
    frame_rate = 30  # Hz
    frame_time = 1.0 / frame_rate
    
    print(f"Processing {num_frames} frames at {frame_rate} Hz...\n")
    
    start_time = time.time()
    for frame_idx in range(num_frames):
        # Generate test frame
        frame = generate_test_frame(frame_idx)
        
        # Get current timestamp
        timestamp = time.time() - start_time
        
        # Process frame
        processed = manager.process_frame(frame, timestamp)
        
        if processed and frame_idx % 5 == 0:  # Print every 5 frames
            pose = manager.get_latest_pose()
            if pose is not None:
                pos = pose.get("position", (0.0, 0.0, 0.0))
                ori = pose.get("orientation", (1.0, 0.0, 0.0, 0.0))
                is_mock = pose.get("is_mock", False)
                
                status = "[MOCK]" if is_mock else "[REAL]"
                print(f"{status} Frame {frame_idx:3d}: Position X={pos[0]:7.4f}, Y={pos[1]:7.4f}, Z={pos[2]:7.4f}")
        
        # Sleep to maintain frame rate (optional)
        time.sleep(frame_time * 0.1)  # Faster for testing
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    # Print final pose
    final_pose = manager.get_latest_pose()
    if final_pose:
        pos = final_pose.get("position", (0.0, 0.0, 0.0))
        ori = final_pose.get("orientation", (1.0, 0.0, 0.0, 0.0))
        print(f"\nFinal Position: X={pos[0]:.4f}, Y={pos[1]:.4f}, Z={pos[2]:.4f}")
        print(f"Final Orientation: W={ori[0]:.4f}, X={ori[1]:.4f}, Y={ori[2]:.4f}, Z={ori[3]:.4f}")
    
    print("\nThe system is ready for integration with ROS 2!")
    print("Build with: colcon build")
    print("Launch with: ros2 launch mvp_system.launch.py")


if __name__ == "__main__":
    main()
