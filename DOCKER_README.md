# AirSniff Docker Deployment Guide

This guide explains how to build and run the AirSniff system using Docker.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose 1.29+ installed (optional but recommended)
- WiFi adapter that supports monitor mode (for WiFi scanning functionality)
- Sufficient disk space (~5GB for image)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# Attach to the container
docker-compose exec airsniff /bin/bash

# Inside the container, launch the system
ros2 launch launch/mvp_system.launch.py
```

### Option 2: Using Docker CLI

```bash
# Build the image
docker build -t airsniff:latest .

# Run the container
docker run -it --privileged --network host \
  -v $(pwd)/logs:/workspace/logs \
  -v $(pwd)/config:/workspace/config \
  --device /dev/net/tun \
  airsniff:latest

# Inside the container, launch the system
ros2 launch launch/mvp_system.launch.py
```

## Building the Docker Image

```bash
# Build with default settings
docker build -t airsniff:latest .

# Build with specific tag
docker build -t airsniff:v1.0 .

# Build without cache (clean build)
docker build --no-cache -t airsniff:latest .
```

## Running the Container

### Interactive Mode (Development)

```bash
# Using docker-compose
docker-compose up -d
docker-compose exec airsniff /bin/bash

# Using docker run
docker run -it --privileged --network host \
  -v $(pwd)/ros2_ws:/workspace/ros2_ws \
  -v $(pwd)/logs:/workspace/logs \
  --device /dev/net/tun \
  airsniff:latest /bin/bash
```

### Running Specific Nodes

```bash
# VIO node
docker-compose exec airsniff ros2 run vio_node vio

# VIO mock node (for testing without camera)
docker-compose exec airsniff ros2 run vio_node vio_mock

# WiFi scanner node
docker-compose exec airsniff ros2 run wifi_scanner_node wifi_scanner

# Data fusion node
docker-compose exec airsniff ros2 run data_fuser_node heatmap_mapper

# IMU node
docker-compose exec airsniff ros2 run fc-imu-node fc_imu_node
```

### Running the Full System

```bash
# Launch all nodes
docker-compose exec airsniff ros2 launch launch/mvp_system.launch.py
```

## Volume Mappings

The docker-compose.yml maps the following directories:

- `./ros2_ws` → `/workspace/ros2_ws` - ROS2 workspace for development
- `./config` → `/workspace/config` - Configuration files
- `./launch` → `/workspace/launch` - Launch files
- `./logs` → `/workspace/logs` - Output logs and data
- `./output` → `/workspace/output` - Generated outputs (GLB files, etc.)

## WiFi Monitor Mode Setup

The container requires privileged mode to access WiFi hardware for monitor mode:

```bash
# Check WiFi interface inside container
docker-compose exec airsniff iwconfig

# Set monitor mode (inside container)
docker-compose exec airsniff /bin/bash
ip link set wlan0 down
iw dev wlan0 set monitor none
ip link set wlan0 up
iwconfig wlan0  # Should show Mode:Monitor
```

## Network Configuration

The container uses `network_mode: host` to:
- Access WiFi hardware directly
- Enable monitor mode operation
- Allow ROS2 node discovery without additional configuration

For multi-machine ROS2 setups, modify `ROS_DOMAIN_ID` and `ROS_LOCALHOST_ONLY` in docker-compose.yml.

## Environment Variables

Configure these in docker-compose.yml or pass via `-e` flag:

- `ROS_DOMAIN_ID=0` - ROS2 domain ID (0-101)
- `ROS_LOCALHOST_ONLY=0` - Set to 1 to restrict ROS2 to localhost
- `DISPLAY=${DISPLAY}` - For GUI applications (RViz, etc.)

## Development Workflow

### Rebuilding After Code Changes

```bash
# If you modified ROS2 packages
docker-compose exec airsniff /bin/bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Adding New Python Dependencies

```bash
# Method 1: Install temporarily (lost on container restart)
docker-compose exec airsniff pip3 install <package>

# Method 2: Add to Dockerfile and rebuild
# Edit Dockerfile, add package to pip install list
docker-compose build
docker-compose up -d
```

### Debugging

```bash
# View container logs
docker-compose logs -f airsniff

# Check running processes
docker-compose exec airsniff ps aux

# Monitor ROS2 topics
docker-compose exec airsniff ros2 topic list
docker-compose exec airsniff ros2 topic echo /wifi/rssi

# Check ROS2 nodes
docker-compose exec airsniff ros2 node list
```

## Jetson Deployment

For NVIDIA Jetson devices, use the Jetson-specific base image:

```dockerfile
# Modify Dockerfile first line:
FROM dustynv/ros:humble-desktop-l4t-r35.1.0

# Or for Jetson Orin:
FROM dustynv/ros:humble-desktop-l4t-r36.2.0
```

Then build on the Jetson device:

```bash
docker build -t airsniff:jetson .
docker-compose up -d
```

## Performance Optimization

### Reduce Image Size

```dockerfile
# Use slim base image (modify Dockerfile)
FROM osrf/ros:humble-ros-base

# Remove unnecessary packages after installation
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
```

### Multi-stage Build

For production deployment, consider a multi-stage build to reduce image size.

## Troubleshooting

### WiFi Adapter Not Found

```bash
# Check USB devices
docker-compose exec airsniff lsusb

# Check network interfaces
docker-compose exec airsniff ip link show

# Ensure --privileged flag is set
# Ensure --device /dev/net/tun is mapped
```

### Permission Denied Errors

```bash
# Ensure container runs with privileged mode
# Check docker-compose.yml has: privileged: true

# Or add specific capabilities
# cap_add:
#   - NET_ADMIN
#   - NET_RAW
```

### ROS2 Nodes Not Communicating

```bash
# Check ROS_DOMAIN_ID matches across containers
docker-compose exec airsniff printenv | grep ROS

# Verify network_mode: host is set
# Check firewall settings on host
```

### Build Failures

```bash
# Clean build cache
docker builder prune

# Build with verbose output
docker build --progress=plain -t airsniff:latest .

# Check disk space
docker system df
```

## Stopping and Cleaning Up

```bash
# Stop the container
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Remove the image
docker rmi airsniff:latest

# Clean up all unused Docker resources
docker system prune -a
```

## Production Deployment

For production deployment on drones:

1. Build the image on the target platform (Jetson)
2. Use `restart: always` in docker-compose.yml
3. Configure automatic startup on boot
4. Monitor container health
5. Implement logging and error handling
6. Use read-only file systems where possible

```yaml
# Production docker-compose.yml example
services:
  airsniff:
    image: airsniff:latest
    restart: always
    privileged: true
    network_mode: host
    volumes:
      - airsniff-logs:/workspace/logs
    healthcheck:
      test: ["CMD", "ros2", "node", "list"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  airsniff-logs:
```

## Security Considerations

Running containers with `--privileged` and `network_mode: host` bypasses Docker's security isolation:

- Only use on trusted networks
- Implement application-level security
- Monitor container activity
- Use specific capabilities instead of privileged mode when possible
- Regularly update base images

## Additional Resources

- [ROS2 Docker Images](https://hub.docker.com/_/ros)
- [Docker Documentation](https://docs.docker.com/)
- [NVIDIA Jetson Containers](https://github.com/dusty-nv/jetson-containers)

---

**Last Updated:** November 2025
