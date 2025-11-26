# Jetson Deployment Guide - Working Configuration

## 🎯 Summary of Changes That Made It Work

### Critical Fixes Applied on Jetson:

1. **Resource Files Fixed** - Added package names to resource files (was empty before)
   - `ros2_ws/src/wifi_scanner_node/resource/wifi_scanner_node` → Contains "wifi_scanner_node"
   - `ros2_ws/src/vio_node/resource/vio_node` → Contains "vio_node"
   - `ros2_ws/src/data-fuser-node/resource/data_fuser_node` → Contains "data_fuser_node"
   - **Why**: ament_python requires these files to register executables properly

2. **Wrapper Script Created** - `ros2_ws/run_wifi_scanner.sh`
   - Handles sudo execution with correct environment
   - Sets `ROS_DOMAIN_ID=99`
   - Sources ROS2 and workspace setup

3. **Build Configuration** - Built without `--symlink-install`
   - Reason: setuptools compatibility issue on Jetson

---

## 🚀 Deployment Steps for Jetson

### 1. Pull Latest Changes

```bash
cd ~/AirSniff
git stash  # If you have local changes
git pull origin Shen
```

### 2. Build ROS2 Workspace

```bash
cd ~/AirSniff/ros2_ws
colcon build
source install/setup.bash
```

### 3. Verify Executables

```bash
ros2 pkg executables wifi_scanner_node  # Should show: wifi_scanner_node wifi_scanner
ros2 pkg executables vio_node           # Should show: vio_node vio, vio_node vio_mock
ros2 pkg executables data_fuser_node    # Should show: data_fuser_node heatmap_mapper
```

---

## ▶️ Running the Full Pipeline

**You MUST run all 3 nodes with `sudo -E` and `ROS_DOMAIN_ID=99`**

### Terminal 1: Mock VIO Node

```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99
source install/setup.bash
sudo -E bash -c "export ROS_DOMAIN_ID=99 && source install/setup.bash && ./install/vio_node/bin/vio_mock"
```

### Terminal 2: WiFi Scanner Node

```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99
sudo ./run_wifi_scanner.sh
```

### Terminal 3: Data Fusion Node

```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99
source install/setup.bash
sudo -E bash -c "export ROS_DOMAIN_ID=99 && source install/setup.bash && ./install/data_fuser_node/bin/heatmap_mapper"
```

### Terminal 4: Monitor (Optional)

```bash
cd ~/AirSniff/ros2_ws
export ROS_DOMAIN_ID=99
source install/setup.bash

# List nodes
ros2 node list

# List topics
ros2 topic list

# Monitor topic rates
ros2 topic hz /wifi/rssi
ros2 topic hz /vio/pose

# Watch file growth
watch -n 1 "wc -l logs/fused_heatmap.csv"
```

---

## 📊 Output Files

### CSV Output Location
```
~/AirSniff/ros2_ws/logs/fused_heatmap.csv
```

### CSV Format
```csv
timestamp,x,y,z,qx,qy,qz,qw,bssid,ssid,rssi,channel,quality
2025-11-17 04:12:40.676,0.133333,0.000000,1.500000,0.000000,0.000000,0.000000,1.000000,E6:CB:AC:32:32:A8,FAF-HQ-GUEST,-75,40,Weak
```

### View Data
```bash
cd ~/AirSniff/ros2_ws

# Last 20 rows
tail -20 logs/fused_heatmap.csv

# Count rows
wc -l logs/fused_heatmap.csv

# Count unique networks
cut -d, -f10 logs/fused_heatmap.csv | tail -n +2 | sort | uniq | wc -l

# List all SSIDs
cut -d, -f10 logs/fused_heatmap.csv | tail -n +2 | sort | uniq
```

---

## ⚙️ Configuration Files

### WiFi Scanner Config
**File**: `ros2_ws/src/wifi_scanner_node/config/wifi_params.yaml`
```yaml
wifi_scanner_node:
  ros__parameters:
    interface: "wlP1p1s0"      # Your WiFi interface
    scan_method: "iwlist"       # or "nmcli"
    scan_interval: 2.0          # seconds
    min_rssi: -90               # dBm
    max_rssi: -20               # dBm
```

### Mock VIO Config
**File**: `ros2_ws/src/vio_node/config/vio_mock_params.yaml`
```yaml
vio_mock:
  ros__parameters:
    motion_pattern: "square"    # hover, line, circle, square, figure8
    update_rate: 10.0           # Hz
    speed: 0.5                  # m/s
    scale: 5.0                  # meters
    height: 1.5                 # meters
```

### Fusion Node Config
**File**: `ros2_ws/src/data-fuser-node/config/fusion_params.yaml`
```yaml
heatmap_mapper_node:
  ros__parameters:
    output_dir: "logs"
    output_file: "fused_heatmap.csv"
    target_ssid: ""             # Empty = all networks
    min_rssi: -90               # Filter weak signals
```

---

## 🔧 Troubleshooting

### Issue: "No executable found"
**Solution**: Resource files must contain package name
```bash
cd ~/AirSniff/ros2_ws/src/wifi_scanner_node
echo "wifi_scanner_node" > resource/wifi_scanner_node
cd ~/AirSniff/ros2_ws
colcon build --packages-select wifi_scanner_node
```

### Issue: Topics not visible
**Solution**: Ensure `ROS_DOMAIN_ID=99` is set in ALL terminals
```bash
export ROS_DOMAIN_ID=99
```

### Issue: WiFi scanner fails
**Solution**: Must run with sudo
```bash
sudo ./run_wifi_scanner.sh
```

### Issue: Nodes can't see each other
**Solution**: All nodes must run with same `ROS_DOMAIN_ID` and sudo
```bash
# Every terminal:
export ROS_DOMAIN_ID=99
sudo -E bash -c "export ROS_DOMAIN_ID=99 && source install/setup.bash && <command>"
```

---

## ✅ Verification Checklist

- [ ] All 3 packages build successfully
- [ ] `ros2 pkg executables` shows all executables
- [ ] All nodes appear in `ros2 node list`
- [ ] Topics `/wifi/rssi` and `/vio/pose` exist
- [ ] `logs/fused_heatmap.csv` is being written
- [ ] CSV file size is growing
- [ ] Data contains position and WiFi info

---

## 📦 System Architecture

```
┌─────────────────┐
│ WiFi Scanner    │──────┐
│ (iwlist/nmcli)  │      │
└─────────────────┘      │
                         ├──> /wifi/rssi (JSON)
┌─────────────────┐      │
│ VIO Node        │──────┤
│ (Mock/Real)     │      │
└─────────────────┘      └──> /vio/pose (PoseStamped)
                                    │
                                    │
                         ┌──────────▼──────────┐
                         │  Data Fusion Node   │
                         │  (Heatmap Mapper)   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         logs/fused_heatmap.csv
```

---

## 🎯 Next Steps

1. **Switch to Real VIO**: When hardware arrives, replace `vio_mock` with `vio`
2. **Optimize Scan Parameters**: Adjust intervals and RSSI filters
3. **Data Visualization**: Create 3D heatmap from CSV
4. **Deploy on Drone**: Mount hardware and test in flight

---

## 📝 Notes

- **Sudo Required**: WiFi scanning needs root privileges
- **ROS_DOMAIN_ID**: Use 99 to isolate from other ROS systems
- **Mock Data**: VIO mock uses simulated square pattern (5m × 5m)
- **Real Data**: WiFi networks are REAL scans from environment
- **CSV Format**: Compatible with most visualization tools

---

**Last Updated**: 2025-11-17  
**Status**: ✅ FULLY WORKING ON JETSON  
**Commit**: 5a30aad

