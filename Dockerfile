# AirSniff Dockerfile - ROS2 Humble + VIO + WiFi RSSI Fusion System
# Base image: ROS2 Humble on Ubuntu 22.04
FROM osrf/ros:humble-desktop

# Avoid prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    python3-pip \
    python3-dev \
    build-essential \
    git \
    wget \
    curl \
    # WiFi monitoring tools
    wireless-tools \
    iw \
    aircrack-ng \
    libpcap-dev \
    net-tools \
    # ROS2 Python packages
    python3-colcon-common-extensions \
    python3-rosdep \
    # Additional utilities
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Core packages for WiFi monitoring and data processing
RUN pip3 install --no-cache-dir \
    scapy \
    pandas \
    numpy \
    PyYAML \
    matplotlib \
    seaborn \
    plotly \
    scipy \
    psutil \
    dataclasses-json \
    pygltflib

# Copy the project files
COPY . /workspace/

# Set up ROS2 workspace
WORKDIR /workspace/ros2_ws

# Initialize rosdep if not already initialized
RUN rosdep update || true

# Install ROS2 dependencies
RUN . /opt/ros/humble/setup.sh && \
    rosdep install --from-paths src --ignore-src -r -y || true

# Build the ROS2 workspace
RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install

# Set up entrypoint to source ROS2 and workspace
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Source ROS2\n\
source /opt/ros/humble/setup.bash\n\
\n\
# Source workspace if built\n\
if [ -f /workspace/ros2_ws/install/setup.bash ]; then\n\
  source /workspace/ros2_ws/install/setup.bash\n\
fi\n\
\n\
exec "$@"' > /ros_entrypoint.sh && \
    chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

# Expose any ports if needed (optional)
# EXPOSE 8080

# Set environment variables
ENV ROS_DOMAIN_ID=0
ENV ROS_LOCALHOST_ONLY=1

# Working directory for running nodes
WORKDIR /workspace
