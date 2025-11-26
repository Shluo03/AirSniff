# 🚀 Quick Demo Deployment Guide

## Hardware Setup (Before Starting)

1. **Connect Flight Controller** → USB to Jetson
2. **Connect Camera** → CSI port 0 on Jetson
3. **Power everything on**

---

## Jetson Deployment Steps

### 1. Pull Latest Code

```bash
cd ~/AirSniff
git pull origin Shen
```

### 2. Build VIO Node

```bash
cd ros2_ws
colcon build --packages-select vio_node
source install/setup.bash
```

### 3. Verify Hardware Connections

```bash
# Check Flight Controller connection
ls /dev/serial/by-id/
# Should see: usb-CubePilot_CubeOrange+_...

# Test camera (Ctrl+C to exit)
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! 'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1' ! nvoverlaysink
```

### 4. Run Full System (3 Terminals)

#### Terminal 1: Real VIO Node
```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99
source install/setup.bash

# Run REAL VIO (replaces mock!)
ros2 run vio_node vio
```

**Expected Output:**
```
[INFO] [vio_node]: Starting IMU and Camera...
[INFO] [IMU] Waiting for heartbeat...
[INFO] [IMU] Connected to system X
[INFO] [CAM] Camera opened at 640x480 @ 30fps
[INFO] [VIO] Initialized with focal length: 512.0px
[WARN] [VIO] Output is unscaled - position not in meters
[INFO] [vio_node]: VIO Node Started
[INFO] Frame 30 | Pos: x=0.123 y=0.456 z=0.789
```

#### Terminal 2: WiFi Scanner
```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99

# Create run script if missing
cat > run_wifi_scanner.sh << 'EOF'
#!/bin/bash
export ROS_DOMAIN_ID=99
source /opt/ros/humble/setup.bash
source install/setup.bash
exec python3 install/wifi_scanner_node/lib/python3.10/site-packages/wifi_scanner_node/wifi_scanner.py "$@"
EOF
chmod +x run_wifi_scanner.sh

sudo ./run_wifi_scanner.sh
```

#### Terminal 3: Fusion Node
```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99
source install/setup.bash

sudo -E bash -c "export ROS_DOMAIN_ID=99 && source install/setup.bash && ./install/data_fuser_node/bin/heatmap_mapper"
```

**Expected Output:**
```
[INFO] [heatmap_mapper_node]: Heatmap Mapper Node Started
[INFO] [heatmap_mapper_node]: Waiting for pose and WiFi data...
[INFO] [heatmap_mapper_node]: Logged 87 networks at pos(0.13, 0.25, 1.42) | Total: 87
```

---

## 5. Verify System is Working

Open a 4th terminal:

```bash
export ROS_DOMAIN_ID=99
source ~/AirSniff/ros2_ws/install/setup.bash

# Check all nodes running
ros2 node list
# Should show:
#   /vio_node
#   /wifi_scanner_node
#   /heatmap_mapper_node

# Check VIO publishing rate
ros2 topic hz /vio/pose
# Should show ~30Hz

# Monitor output file
cd ~/AirSniff/ros2_ws
watch -n 1 "wc -l logs/fused_heatmap.csv"
```

---

## 6. Collect Demo Data

**Walk around the room slowly** with the Jetson + camera. The system will:
- Track your position via VIO (camera + IMU)
- Scan WiFi networks continuously
- Log both to `logs/fused_heatmap.csv`

**Demo time: 2-3 minutes of walking**

---

## 7. Stop System & Download Data

```bash
# Stop all nodes: Ctrl+C in each terminal

# Download CSV to Mac
# On Mac:
scp jetson@jetson:~/AirSniff/ros2_ws/logs/fused_heatmap.csv ~/Desktop/
```

---

## 🔧 Troubleshooting

### VIO Node Issues

**Problem:** `[IMU] Error: ...` or no heartbeat
- **Fix:** Check USB connection, try different port
- **Fix:** Verify FC port: `ls /dev/serial/by-id/`

**Problem:** `[CAM] Frame grab failed`
- **Fix:** Check camera connection to CSI port 0
- **Fix:** Verify with: `v4l2-ctl --list-devices`

**Problem:** Low feature count / no motion detected
- **Fix:** Better lighting
- **Fix:** More visual features (textured walls, not blank)

### WiFi Scanner Issues

**Problem:** `Interface doesn't support scanning: Device busy`
- **Fix:** Wait a few seconds, it's temporary
- **Fix:** Try: `sudo nmcli dev wifi rescan`

### Fusion Node Issues

**Problem:** `[WARN] Skipping WiFi data - no pose received yet`
- **Fix:** Ensure VIO node (Terminal 1) is running first
- **Fix:** Check `ROS_DOMAIN_ID=99` in ALL terminals

---

## 📊 Quick Status Check

```bash
# One-liner to check everything
export ROS_DOMAIN_ID=99 && source ~/AirSniff/ros2_ws/install/setup.bash && echo "=== NODES ===" && ros2 node list && echo "=== TOPICS ===" && ros2 topic list && echo "=== VIO HZ ===" && timeout 3 ros2 topic hz /vio/pose 2>&1 || echo "VIO not publishing"
```

---

## 🎯 Success Criteria

✅ VIO node shows position updates every 30 frames  
✅ WiFi scanner logs ~90-100 networks per scan  
✅ Fusion node shows increasing "Total: XXX" count  
✅ CSV file grows over time  
✅ Position values in CSV change as you move (not stuck at 0.0)

---

## 🚨 If Nothing Works

**Nuclear Option - Fresh Build:**

```bash
cd ~/AirSniff/ros2_ws
rm -rf build/ install/ log/
colcon build
source install/setup.bash
# Try again from Step 4
```

---

## 📝 Quick Reference

| Component | Rate | Topic | Needs Sudo? |
|-----------|------|-------|-------------|
| VIO Node | 30Hz | `/vio/pose` | No |
| WiFi Scanner | 2Hz | `/wifi/rssi` | **Yes** |
| Fusion Node | Variable | - | **Yes** |

**Important:** Run WiFi scanner and fusion node with `sudo` for network access!

