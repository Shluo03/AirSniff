# Jetson Setup & Running Instructions

## Prerequisites Checklist

Before running on Jetson, make sure you have:

- [ ] Jetson powered on and accessible (SSH or direct)
- [ ] Python 3 installed on Jetson
- [ ] PyYAML installed (`pip install pyyaml`)
- [ ] WiFi adapter connected (interface should be `wlP1p1s0` or check your interface)
- [ ] Sudo/root access

## Step 1: Transfer Files to Jetson

### Option A: Using Git (Recommended)
```bash
# On Jetson
cd ~/Desktop
git clone <your-repo-url> AirSniff
# OR if already cloned:
cd ~/Desktop/AirSniff
git pull origin Shen
```

### Option B: Using SCP (from your Mac)
```bash
# From your Mac terminal
cd ~/Desktop/AirSniff
scp -r wifi_scanner_active.py config/ logs/ jetson@<jetson-ip>:~/Desktop/AirSniff/
```

### Option C: Manual Copy
If you have the files locally, copy them to Jetson via USB drive or network share.

## Step 2: Verify Files on Jetson

```bash
# SSH into Jetson or open terminal on Jetson
cd ~/Desktop/AirSniff

# Verify files exist
ls -la
# Should see:
# - wifi_scanner_active.py
# - config/wifi_config.yaml
# - logs/ directory

# Verify Python can import yaml
python3 -c "import yaml; print('PyYAML OK')"
# If error, install: pip3 install pyyaml
```

## Step 3: Check Your WiFi Interface

**IMPORTANT:** The config file defaults to `wlP1p1s0`. Check your actual interface name:

```bash
# On Jetson
ip link show

# Look for WiFi interface. Common names:
# - wlP1p1s0 (Jetson AGX/Xavier)
# - wlan0
# - wlan1
# - eth0 (if WiFi is bridged)

# Or use iwconfig
iwconfig

# Update config file if your interface is different:
nano config/wifi_config.yaml
# Change: interface: "wlP1p1s0" to your actual interface name
```

## Step 4: Test Configuration Loading (No WiFi Scanning)

```bash
# On Jetson - Test config loading without scanning
cd ~/Desktop/AirSniff
python3 wifi_scanner_active.py --help

# Test with dry-run first (works without sudo)
python3 wifi_scanner_active.py --dry-run --duration 3 --no-continuous

# Verify config loads correctly
python3 -c "import yaml; c=yaml.safe_load(open('config/wifi_config.yaml')); print('Interface:', c['wifi_scanner']['interface'])"
```

## Step 5: Run WiFi Scanner (Actual Scanning)

### Basic Test (5 seconds)
```bash
cd ~/Desktop/AirSniff
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
```

**Expected Output:**
- Configuration banner showing your interface
- Real WiFi networks detected
- Real SSIDs (network names from your environment)
- Real BSSIDs (MAC addresses)
- Real RSSI values
- Networks printed to console

### Console Output Only
```bash
sudo python3 wifi_scanner_active.py --output console --duration 10 --no-continuous
```

### Save to CSV File
```bash
sudo python3 wifi_scanner_active.py --output file --file-path logs/wifi_scan.csv --duration 10 --no-continuous

# Check the CSV file
cat logs/wifi_scan.csv
```

### Both Console and CSV
```bash
sudo python3 wifi_scanner_active.py --output both --file-path logs/wifi_both.csv --duration 10 --no-continuous
```

### Continuous Mode (Until Ctrl+C)
```bash
sudo python3 wifi_scanner_active.py --continuous

# Let it run for 30 seconds, then press Ctrl+C to stop
```

### Custom Scan Interval
```bash
# Scan every 2 seconds for 20 seconds
sudo python3 wifi_scanner_active.py --scan-interval 2.0 --duration 20 --no-continuous
```

### Override Interface Name
```bash
# If your interface is different (e.g., wlan0)
sudo python3 wifi_scanner_active.py --interface wlan0 --duration 5 --no-continuous
```

## Step 6: Verify Output

### Check Console Output
- Should see real network names (not "TestNetwork_*")
- Should see real BSSIDs (not "AA:BB:CC:DD:EE:*")
- Should see varying RSSI values (from your environment)
- RSSI values should be realistic (-30 to -90 dBm range)

### Check CSV File
```bash
# View CSV file
cat logs/wifi_scans.csv

# Count networks found
tail -n +2 logs/wifi_scans.csv | wc -l

# View first few networks
head -10 logs/wifi_scans.csv
```

**CSV Format:**
```
timestamp,scan_number,ssid,bssid,rssi,channel,quality
2024-11-16 10:30:45,1,YourNetworkName,AA:BB:CC:DD:EE:FF,-45,6,Excellent
...
```

## Common Issues & Solutions

### Issue 1: "Permission denied"
**Error:** `❌ ERROR: Permission denied!`

**Solution:**
```bash
# Must use sudo for WiFi scanning
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
```

### Issue 2: "WiFi interface 'wlP1p1s0' does not exist"
**Error:** `❌ Configuration Error: WiFi interface 'wlP1p1s0' does not exist`

**Solution:**
```bash
# Find your actual interface
ip link show

# Update config file
nano config/wifi_config.yaml
# Change interface to your actual name

# OR use CLI override
sudo python3 wifi_scanner_active.py --interface wlan0 --duration 5 --no-continuous
```

### Issue 3: "No networks found"
**Possible causes:**
- WiFi adapter not connected
- WiFi disabled
- No networks in range
- Wrong interface name

**Check:**
```bash
# Verify WiFi is up
ip link show wlP1p1s0  # or your interface

# Check WiFi status
iwconfig wlP1p1s0  # or your interface

# Test iwlist manually
sudo iwlist wlP1p1s0 scan | head -20

# If iwlist fails, try:
sudo nmcli dev wifi list
```

### Issue 4: "Error running iwlist: Device or resource busy"
**Error:** `Error running iwlist: wlP1p1s0 Interface doesn't support scanning : Device or resource busy`

**Cause:** WiFi adapter is in use (connected to a network, or NetworkManager is managing it)

**Solutions:**
```bash
# Option 1: Disconnect from current network first
sudo nmcli radio wifi off
sudo nmcli radio wifi on
# Wait 2 seconds, then try scanning

# Option 2: Stop NetworkManager temporarily (may disconnect you)
sudo systemctl stop NetworkManager
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
sudo systemctl start NetworkManager

# Option 3: Use a different WiFi adapter for scanning (if you have one)
```

### Issue 5: PyYAML not installed
**Error:** `ModuleNotFoundError: No module named 'yaml'`

**Solution:**
```bash
# Install PyYAML
pip3 install pyyaml

# OR if using venv
source venv/bin/activate
pip install pyyaml
```

### Issue 6: iwlist command not found
**Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'iwlist'`

**Solution:**
```bash
# Install wireless tools
sudo apt update
sudo apt install -y wireless-tools

# Verify installation
which iwlist
iwlist --version
```

## Production Usage

### Continuous Scanning for RF Heatmapping
```bash
# Run continuously, save to CSV
sudo python3 wifi_scanner_active.py \
  --output both \
  --file-path logs/rf_heatmap_$(date +%Y%m%d_%H%M%S).csv \
  --continuous \
  --scan-interval 1.5
```

### Long Duration Scan
```bash
# Scan for 5 minutes (300 seconds)
sudo python3 wifi_scanner_active.py \
  --output file \
  --file-path logs/5min_scan.csv \
  --duration 300 \
  --no-continuous \
  --scan-interval 2.0
```

### Custom Configuration File
```bash
# Use a custom config file
sudo python3 wifi_scanner_active.py \
  --config config/jetson_config.yaml \
  --duration 10 \
  --no-continuous
```

## Verification Checklist

After running on Jetson, verify:

- [ ] Scanner runs without errors
- [ ] Real WiFi networks are detected (not test networks)
- [ ] RSSI values are realistic (-30 to -90 dBm)
- [ ] Console output shows real network names
- [ ] CSV file is created (if file output enabled)
- [ ] CSV file has proper header and data rows
- [ ] Timestamps are correct
- [ ] Multiple scans work (if duration > scan_interval)
- [ ] Ctrl+C stops gracefully (if continuous mode)

## Next Steps

Once verified working:
1. Test with longer durations
2. Test continuous mode
3. Test CSV output format with your fusion_logger
4. Verify CSV format matches your fusion_logger expectations
5. Test with drone movement (if applicable)

## Troubleshooting Command Reference

```bash
# Check WiFi interface status
ip link show
iwconfig

# Test iwlist manually
sudo iwlist wlan0 scan | head -30

# Check Python dependencies
python3 -c "import yaml, csv, argparse; print('All OK')"

# Check file permissions
ls -la wifi_scanner_active.py
ls -la config/wifi_config.yaml

# Test config loading
python3 -c "import yaml; print(yaml.safe_load(open('config/wifi_config.yaml')))"

# Check logs directory
ls -la logs/
mkdir -p logs  # if missing
```

---

**Remember:** Always use `sudo` for actual WiFi scanning (not needed for `--dry-run` mode).

