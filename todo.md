## 1. Hardware Setup
* **Mount Hardware:** Securely mount both the camera and IMU to the bracket. **Note:** Any relative motion between the sensors will cause system failure.
---

## 2. Sensor Software (ROS 2)
* **Jetson Camera Node:**
    * Install and configure `gscam` to publish the hardware-accelerated GStreamer pipeline (`nvarguscamerasrc`) to a ROS 2 topic (e.g., `/camera/image_raw`) at 30Hz.
* **ESP32 IMU Node:**
    * Follow its setup guide.
* **Jetson Agent Node:**
    * Install and run the `micro-ros-agent` on the Jetson, configured to connect to the ESP32's serial port.
* **Verification:**
    * Confirm a stable 30Hz stream from `ros2 topic hz /camera/image_raw`.
    * Confirm a stable 200Hz stream from `ros2 topic hz /imu/data_raw`.

---

## 3. System Calibration (Offline)
* **Camera Intrinsics:**
    * Run the ROS 2 `camera_calibration` node.
    * Calibrate the RPi camera using a checkerboard target.
    * Save the resulting `camera.yaml` file (containing `D` and `K` matrices).
* **IMU-Camera Extrinsics:**
    * Record a ROS 2 bag file (`ros2 bag record`) of both `/camera/image_raw` and `/imu/data_raw` while moving the *entire rig* smoothly in all 6 degrees of freedom in front of a calibration target (e.g., Aprilgrid).
    * Convert the ROS 2 bag to a ROS 1 `.bag` file (e.g., using `rosbags-convert`).
    * Run the **Kalibr** tool (e.g., in Docker) to process the `.bag` file.
    * Save the resulting `extrinsics.yaml` file, which contains the critical `T_cam_imu` 4x4 transformation matrix.

---

## 4. VIO Implementation (Online)
* **Install VIO System:** Install a compatible VIO package, such as the ROS 2 Humble wrapper for **ORB-SLAM3** or **Isaac ROS vSLAM** (run in monocular-inertial mode).
* **Configure VIO Node:**
    * Create a new VIO configuration file (e.g., `jetson_config.yaml`).
    * Copy all parameters from the **Camera Intrinsics** (`camera.yaml`) into this file.
    * Copy all parameters (especially the `T_cam_imu` matrix) from the **Extrinsics** (`extrinsics.yaml`) into this file.
    * Set the `Camera.fps` to 30 and `IMU.Frequency` to 200.
* **Create Master Launch File:**
    * Write a single ROS 2 launch file (`.launch.py`) that:
        1.  Starts the `gscam` camera node.
        2.  Starts the `micro-ros-agent`.
        3.  Launches the VIO node, loading your `jetson_config.yaml` as a parameter.
* **Execute and Visualize:**
    * Launch the master file.
    * Move the rig slowly to allow the VIO system to initialize.
    * Visualize the output pose topic (e.g., `/orb_slam3/pose`) in RViz2 to see the `pos x y z` tracking in real-time.


## 5. WiFi Heatmap Generation (Online)
* **Create Heatmap Package:** Create a new ROS 2 package (e.g., `my_heatmap_pkg`) to hold the mapping node.
* **Develop Mapper Node:**
    * Create a new Python-based ROS 2 node (e.g., `heatmap_mapper_node.py`).
    * **Add Subscriber:** Implement a subscriber that listens to the VIO's pose topic (e.g., `/vio/pose` or `/orb_slam3/pose`) and stores the latest `pos x y z` data in a class variable.
    * **Add Timer:** Implement a ROS 2 Timer that runs at a slow, fixed rate (e.g., every 2.0 seconds).
    * **Implement Scan Logic:** Port your Python WiFi scanning functions (`scan_wifi_iwlist`, etc.) into this node.
    * **Fuse Data:** Program the timer's callback function to:
        1.  Call the `scan_wifi_iwlist` function (a blocking operation).
        2.  Immediately read the `self.last_known_pose` variable.
        3.  Filter for the target WiFi network(s).
        4.  Combine the `(x, y, z)` pose with the `(rssi)` signal strength.
        5.  Write the fused `(timestamp, x, y, z, rssi)` data to a CSV log file.
* **Update Master Launch File:**
    * Add the new `heatmap_mapper_node` to your `start_vio.launch.py` file.
    * This ensures the camera, IMU agent, VIO node, and heatmap node all launch with a single command.
* **Execute and Verify:**
    * Run the master launch file and move the rig around your target area.
    * After the run, inspect the `heatmap_log.csv` file to confirm that pose and signal strength data were successfully logged together.


## 6. Create One-Step Startup Script
* **Create Bash Script:** In the root of your project repository, create a new file named `run_heatmap.sh`.
* **Add Script Commands:** Edit the `run_heatmap.sh` file and add the necessary commands to:
    1.  **Source ROS 2:** Add the line `source /opt/ros/humble/setup.bash` to load the main ROS environment.
    2.  **Source Workspace:** Add the line `source ~/ros2_ws/install/setup.bash` to load your custom packages.
    3.  **Run Master Launch File:** Add the line `ros2 launch my_vio_launch_pkg start_vio.launch.py` to execute the master launch file that starts the camera, IMU, VIO, and heatmap nodes.
* **Make Script Executable:** Run the command `chmod +x run_heatmap.sh` to give the script permission to run.
* **Execute:** The entire system (VIO pose generation and WiFi data logging) can now be started by running the single command: `./run_heatmap.sh` in the project's root directory.