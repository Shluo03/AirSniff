# AirSniff: 3D VIO WiFi Heatmap Generator

This project implements a complete 3D mapping system to generate WiFi signal strength heatmaps. It uses a Monocular Visual-Inertial Odometry (VIO) system to generate a real-time 3D position (`pos x y z`) for a sensor rig.

This pose data is then fused with WiFi signal (RSSI) scans to create a timestamped log of `(x, y, z, rssi)`, which can be used to build 3D heatmaps.

-----

## Key Features

  * **Real-time VIO:** Generates a 6-DOF pose from a single Raspberry Pi camera and an ESP32-based IMU.
  * **Sensor Fusion:** Runs on ROS 2 Humble, fusing high-speed IMU data (200Hz) from `micro-ROS` and camera data (30Hz) from a hardware-accelerated `gscam` pipeline.
  * **WiFi Mapping:** Includes a dedicated ROS 2 node that subscribes to the pose and runs WiFi scans, logging the fused data.
  * **One-Step Launch:** The entire system (camera, IMU, VIO, and WiFi mapper) is launched with a single script.

-----

## Hardware Requirements

  * **Compute:** NVIDIA Jetson Orin NX
  * **Vision:** Raspberry Pi Camera (MIPI-CSI)
  * **Inertial:** ESP32 (e.g., ESP32-C3) with an ICM-42670 IMU
  * **Mount:** A **rigid 3D-printed mount** is required to ensure the camera and IMU have zero relative motion.

-----

## 🚀 Quick Start

**Prerequisite:** All hardware is connected and the system has been calibrated (see below).

To start the entire VIO system and begin logging heatmap data, simply run the master script:

```bash
./run_heatmap.sh
```

This will:

1.  Source the ROS 2 environment.
2.  Launch the master launch file (`start_heatmap.launch.py`).
3.  Start all nodes: Camera, IMU Agent, VIO, and Heatmap Mapper.
4.  Begin logging data to `heatmap_log.csv`.

-----

## Calibration (CRITICAL)

This system **will not work** without proper offline calibration. The VIO node depends on pre-generated config files.

You must run the following calibration routines and place the resulting `.yaml` files in the `src/master_launch_pkg/config/` directory.

1.  **Camera Intrinsics:** Run the ROS 2 `camera_calibration` node to find your camera's focal length and distortion.
2.  **IMU Intrinsics:** Run the `imu_calib` node to measure the IMU's noise and random walk.
3.  **Camera-IMU Extrinsics:** Run **Kalibr** to find the precise 3D transformation (`T_cam_imu`) between the camera sensor and the IMU chip.

-----

## Repository Structure

The project is organized as a ROS 2 workspace.

```text
jetson_vio_heatmap/       <-- Git repo root
├── .gitignore
├── run_heatmap.sh          <-- One-step launch script
├── src/                    <-- ROS 2 packages
│   │
│   ├── jetson_camera_pkg/  <-- Package for the gscam (camera) node
│   │   ├── launch/
│   │   │   └── camera.launch.py
│   │   └── package.xml
│   │
│   ├── esp32_imu_firmware/ <-- Standalone ESP-IDF firmware for the IMU
│   │   ├── main/
│   │   │   └── main.c
│   │   └── ... (Other ESP-IDF project files)
│   │
│   ├── heatmap_mapper_pkg/ <-- Package for the WiFi scanning & data logging node
│   │   ├── heatmap_mapper_pkg/
│   │   │   └── heatmap_node.py
│   │   └── package.xml
│   │
│   └── master_launch_pkg/  <-- Master package for launching and configuration
│       ├── launch/
│       │   └── start_heatmap.launch.py  <-- The master launch file
│       ├── config/
│       │   ├── 01_camera_intrinsics.yaml  <-- from camera_calibration
│       │   ├── 02_imu_noise.yaml          <-- from imu_calib
│       │   ├── 03_camera_imu_extrinsics.yaml <-- from Kalibr
│       │   └── 04_vio_params.yaml         <-- VIO-specific settings
│       └── package.xml
│
└── README.md
```