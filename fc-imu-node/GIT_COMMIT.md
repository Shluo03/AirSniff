# Files to Commit for fc-imu-node

## All Source Files (Commit These)

```bash
# Core package files
fc-imu-node/package.xml
fc-imu-node/setup.py
fc-imu-node/setup.cfg

# Python source code
fc-imu-node/fc_imu_node/__init__.py
fc-imu-node/fc_imu_node/fc_imu_node.py

# Launch files
fc-imu-node/launch/fc_imu_node.launch.py

# Resource marker
fc-imu-node/resource/fc_imu_node

# Documentation
fc-imu-node/README.md
fc-imu-node/setup_guide.md
fc-imu-node/DEPLOYMENT.md

# Git ignore
fc-imu-node/.gitignore
```

## Quick Commit Command

```bash
cd /path/to/AirSniff

# Add all fc-imu-node files
git add fc-imu-node/

# Verify what will be committed
git status

# Commit
git commit -m "Add fc-imu-node: ROS 2 IMU node for flight controller via MAVLink"
```

## Note

The old file `fc-imu-node/fc_imu_node.py` (in root) was moved to `fc-imu-node/fc_imu_node/fc_imu_node.py` (in package directory). Git will handle this as a deletion of the old file and addition of the new one.

