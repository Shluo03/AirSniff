# Quick Start - Jetson

## 🚀 Fastest Way to Get Started

### Step 1: Verify Files
```bash
cd ~/Desktop/AirSniff
ls -la wifi_scanner_active.py config/wifi_config.yaml
```

### Step 2: Check WiFi Interface
```bash
ip link show
# Note your WiFi interface name (e.g., wlP1p1s0, wlan0)
```

### Step 3: Update Config (if needed)
```bash
nano config/wifi_config.yaml
# Change interface: "wlP1p1s0" to your actual interface name
```

### Step 4: Test First Run (5 seconds)
```bash
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
```

**Expected:** Real WiFi networks printed to console

---

## 📋 Common Commands

### Basic Scan (Console Only)
```bash
sudo python3 wifi_scanner_active.py --duration 10 --no-continuous
```

### Save to CSV File
```bash
sudo python3 wifi_scanner_active.py --output file --duration 10 --no-continuous
cat logs/wifi_scans.csv
```

### Both Console + CSV
```bash
sudo python3 wifi_scanner_active.py --output both --duration 10 --no-continuous
```

### Continuous Mode
```bash
sudo python3 wifi_scanner_active.py --continuous
# Press Ctrl+C to stop
```

### Different Interface
```bash
sudo python3 wifi_scanner_active.py --interface wlan0 --duration 5 --no-continuous
```

---

## ⚠️ Common Issues

**"Permission denied"**  
→ Use `sudo`

**"Interface does not exist"**  
→ Check: `ip link show`  
→ Update config or use `--interface <name>`

**"No networks found"**  
→ Check: `sudo iwlist wlP1p1s0 scan | head -20`

**"Device busy"**  
→ Disconnect from current WiFi network first

---

## 📝 Full Documentation

See `JETSON_SETUP.md` for detailed instructions and troubleshooting.

