# Setup Instructions

Complete setup guide for the AirSniff WiFi RF Heatmap project.

## Quick Setup (5 Minutes)

```bash
# 1. Clone repository
git clone <repo-url>
cd AirSniff

# 2. Setup virtual environment
./setup_venv.sh

# 3. Activate environment
source venv/bin/activate

# 4. Install system dependencies (Jetson/Ubuntu only)
sudo apt install -y wireless-tools iw aircrack-ng
```

Done! You're ready to develop.

---

## Detailed Setup

### 1. Virtual Environment Setup

The project uses a Python virtual environment for dependency management.

**Automated Setup (Recommended):**
```bash
./setup_venv.sh
```

When prompted, choose:
- **1 - Minimal** (~50 MB): Core WiFi monitoring only
  - Packages: scapy, pandas, numpy, PyYAML
  - Use for: Jetson production deployment

- **2 - Standard** (~300 MB): WiFi + visualization [Default]
  - Adds: matplotlib, seaborn, plotly, scipy, psutil
  - Use for: Most development work

- **3 - Full** (~500 MB): Everything including dev tools
  - Adds: pytest, black, pylint, jupyter, and more
  - Use for: Complete development environment

**Manual Setup (Alternative):**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Minimal installation
pip install scapy pandas numpy PyYAML

# OR Standard installation (recommended)
pip install scapy pandas numpy PyYAML matplotlib seaborn plotly scipy psutil

# OR Full installation
pip install -r requirements.txt
```

**Daily Activation:**
```bash
# Every time you work on the project
source venv/bin/activate

# Or use helper script
source activate_venv.sh

# When done
deactivate
```

### 2. System Dependencies

**On Jetson/Ubuntu:**
```bash
sudo apt update
sudo apt install -y \
  python3-dev \
  build-essential \
  wireless-tools \
  iw \
  aircrack-ng \
  libpcap-dev
```

**For ROS 2:**
```bash
sudo apt install -y \
  ros-humble-rclpy \
  ros-humble-std-msgs \
  ros-humble-geometry-msgs
```

**For pycuVSLAM (SLAM developers):**
Follow NVIDIA's official guide:
https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam

### 3. WiFi Adapter Setup

**Check if your adapter supports monitor mode:**
```bash
# List interfaces
iwconfig

# Check supported modes
iw list | grep -A 5 "Supported interface modes"
```

Look for "monitor" in the output.

**Test monitor mode:**
```bash
# Set monitor mode (requires sudo)
sudo ip link set wlan0 down
sudo iw dev wlan0 set monitor none
sudo ip link set wlan0 up
iwconfig wlan0  # Should show "Mode:Monitor"

# Restore managed mode when done
sudo ip link set wlan0 down
sudo iw dev wlan0 set type managed
sudo ip link set wlan0 up
```

**Recommended WiFi Adapters (if needed):**
- **Alfa AWUS036ACH** ($50) - Dual-band, excellent monitor mode
- **TP-Link TL-WN722N v1** ($15) - Budget option, 2.4GHz only
- **Panda PAU09** ($25) - Good Linux support

**Note:** Version matters! For TP-Link, only **v1** supports monitor mode.

---

## Platform-Specific Notes

### macOS Development

**Limitations:**
- Built-in WiFi cannot enter monitor mode
- No `iw` command (Linux-only)
- Limited packet capture capabilities

**What works:**
- Virtual environment setup
- Python package installation
- Code development
- Visualization work
- ROS2 node structure (without actual WiFi scanning)

**Recommendation:**
Develop on macOS, test on Jetson or Linux VM.

### Jetson Production

**Advantages:**
- Full monitor mode support
- ROS 2 Humble compatibility
- GPU-accelerated SLAM
- Production target platform

**Optimizations:**
- Use minimal installation to save space
- Install only required packages
- Consider read-only rootfs for production

### Linux Desktop

Similar to Jetson, full functionality with proper WiFi adapter.

---

## Troubleshooting

### Virtual Environment Issues

**"setup_venv.sh: Permission denied"**
```bash
chmod +x setup_venv.sh activate_venv.sh
./setup_venv.sh
```

**"venv not found"**
```bash
# Recreate virtual environment
rm -rf venv
./setup_venv.sh
```

**"pip: command not found"**
```bash
# Inside venv, this shouldn't happen
deactivate
source venv/bin/activate
pip --version
```

### WiFi Adapter Issues

**"Interface not found"**
```bash
# Check all interfaces
ip link show
iwconfig

# Your interface might be wlan1, wlan2, etc.
# Update config/wifi_config.yaml accordingly
```

**"Monitor mode not supported"**
```bash
# Check chipset support
lsusb  # For USB adapters
lspci  # For internal adapters

# Check driver capabilities
iw list | grep monitor

# If not supported, need different adapter
```

**"Permission denied" when capturing packets**
```bash
# Option 1: Run with sudo (not ideal for ROS2)
sudo python your_script.py

# Option 2: Set capabilities (recommended)
sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)

# Option 3: Add udev rule (best for production)
# Create /etc/udev/rules.d/80-wifi-monitor.rules:
# SUBSYSTEM=="net", ATTR{dev_id}=="0x0", KERNEL=="wlan*", MODE="0666"
sudo udevadm control --reload-rules
```

**"No RSSI in captured packets"**
```bash
# Some adapters don't expose RSSI in RadioTap headers
# Try different adapter or check adapter specifications
```

### ROS 2 Issues

**"rclpy not found"**
```bash
# Don't install via pip! Use apt:
sudo apt install ros-humble-rclpy ros-humble-std-msgs

# Then activate both ROS and venv:
source /opt/ros/humble/setup.bash
source venv/bin/activate
```

**"Package not found after colcon build"**
```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep wifi_monitor
```

### Package Installation Issues

**"Some packages failed to install"**
```bash
# Update pip first
pip install --upgrade pip setuptools wheel

# Try installing problematic package individually
pip install <package-name>

# Check for missing system libraries
# See requirements.txt for system dependencies
```

**"Incompatible package versions"**
```bash
# Generate locked requirements
pip freeze > requirements-lock.txt

# Clean install
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-lock.txt
```

---

## Verification Checklist

After setup, verify everything works:

```bash
# ✓ Virtual environment
source venv/bin/activate
python --version  # Should be 3.8+

# ✓ Core packages
python -c "import scapy, pandas, numpy, yaml; print('Core packages OK')"

# ✓ WiFi adapter (if on Jetson/Linux)
iwconfig  # Should show wlan0 or similar

# ✓ ROS 2 (if installed)
ros2 --version  # Should show Humble

# ✓ Project structure
ls ros2_ws/src/wifi_monitor  # Should exist (after creating)
```

---

## Next Steps

After successful setup:

1. **Read TODO.md** - Complete implementation roadmap
2. **Create ROS2 package** - See TODO.md Phase 1
3. **Implement WiFi monitoring** - See TODO.md Phase 3-6
4. **Test integration** - See TODO.md Phase 8-10

---

## Additional Resources

**ROS 2 Documentation:**
- https://docs.ros.org/en/humble/

**Scapy Documentation:**
- https://scapy.readthedocs.io/

**802.11 WiFi:**
- https://www.radiotap.org/ (RadioTap header format)
- https://mrncciew.com/2014/10/08/802-11-mgmt-beacon-frame/

**NVIDIA Isaac ROS:**
- https://github.com/NVIDIA-ISAAC-ROS

---

**Last Updated:** November 15, 2025
**For questions:** See TODO.md or consult with team members
