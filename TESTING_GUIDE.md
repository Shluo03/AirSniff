# WiFi Scanner Testing Guide

## Quick Test Checklist

### Test 1: Configuration Loading ✅
```bash
# On Jetson
cd ~/Desktop/AirSniff
python3 wifi_scanner_active.py --help
```
**Expected:** Shows help menu with all CLI options

### Test 2: Default Config ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
```
**Expected:** 
- Loads config from `config/wifi_config.yaml`
- Uses interface `wlP1p1s0`
- Runs for 5 seconds
- Prints networks to console
- Shows configuration at startup

### Test 3: CLI Override - Interface ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --interface wlP1p1s0 --duration 5 --no-continuous
```
**Expected:** Works with specified interface (if it exists on your Jetson)

### Test 4: Console Output Only ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --output console --duration 5 --no-continuous
```
**Expected:** Only prints to console, no file created

### Test 5: File Output Only ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --output file --file-path logs/test_scan.csv --duration 5 --no-continuous
```
**Expected:** 
- No console output
- Creates `logs/test_scan.csv`
- CSV has header row
- CSV has data rows

### Test 6: Both Console and File ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --output both --file-path logs/both_test.csv --duration 5 --no-continuous
```
**Expected:** 
- Prints to console AND saves to CSV file

### Test 7: Continuous Mode ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --continuous
# Press Ctrl+C after 3-4 scans
```
**Expected:** 
- Runs indefinitely
- Shows "Continuous" in startup banner
- Stops gracefully on Ctrl+C
- Shows scan count summary

### Test 8: Scan Interval Override ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --scan-interval 2.0 --duration 10 --no-continuous
```
**Expected:** 
- 2 second delay between scans
- Should see ~5 scans in 10 seconds

### Test 9: Scan Method Override ✅
```bash
# On Jetson (if nmcli is available)
sudo python3 wifi_scanner_active.py --scan-method nmcli --duration 5 --no-continuous
```
**Expected:** Uses nmcli instead of iwlist (may be faster)

### Test 10: RSSI Filtering ✅
```bash
# On Jetson - only show strong networks
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
# Edit config/wifi_config.yaml to set min_rssi: -70, max_rssi: -20
sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
```
**Expected:** Second run shows fewer networks (only strong signals)

### Test 11: Error Handling ✅
```bash
# Test invalid interface
sudo python3 wifi_scanner_active.py --interface invalid0 --duration 1 --no-continuous
```
**Expected:** Clear error message about interface not existing

### Test 12: Config File Override ✅
```bash
# On Jetson
cp config/wifi_config.yaml config/test_config.yaml
# Edit test_config.yaml (change interface or scan_interval)
sudo python3 wifi_scanner_active.py --config config/test_config.yaml --duration 5 --no-continuous
```
**Expected:** Uses values from `test_config.yaml`

### Test 13: CSV File Format ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --output file --file-path logs/format_test.csv --duration 5 --no-continuous
cat logs/format_test.csv
```
**Expected:** 
- Header: `timestamp,scan_number,ssid,bssid,rssi,channel,quality`
- Each row has all fields
- Timestamps are properly formatted

### Test 14: Multiple Scans CSV ✅
```bash
# On Jetson
sudo python3 wifi_scanner_active.py --output file --file-path logs/multi_scan.csv --duration 10 --no-continuous --scan-interval 2.0
wc -l logs/multi_scan.csv
```
**Expected:** 
- CSV has header + multiple data rows
- One row per network per scan
- Line count = 1 (header) + (number of networks × number of scans)

## Verification Checklist

After running tests, verify:

- [ ] Config file loads correctly
- [ ] CLI arguments override config values
- [ ] Console output shows networks correctly
- [ ] CSV file is created with proper format
- [ ] CSV has header row
- [ ] CSV has data rows
- [ ] Timestamps are in CSV
- [ ] RSSI values are in CSV
- [ ] Continuous mode works (until Ctrl+C)
- [ ] Timed mode works (stops after duration)
- [ ] Error messages are clear
- [ ] Startup banner shows configuration
- [ ] Summary statistics shown on exit

## Common Issues

### Issue: "Permission denied"
**Solution:** Use `sudo` - the scanner needs root permissions to scan WiFi

### Issue: "Interface 'wlP1p1s0' does not exist"
**Solution:** 
1. Check your actual interface: `ip link show`
2. Update `config/wifi_config.yaml` with correct interface name
3. Or use `--interface <your_interface>`

### Issue: "Cannot write to directory 'logs'"
**Solution:** 
```bash
mkdir -p logs
chmod 755 logs
```

### Issue: "No networks found"
**Possible causes:**
- WiFi adapter not connected
- Interface name wrong
- WiFi driver issues
- No WiFi networks in range

**Check:**
```bash
ip link show
iwconfig
sudo iwlist wlP1p1s0 scan | head -20
```

## Performance Testing

### Measure scan rate:
```bash
# Count scans in 30 seconds
timeout 30 sudo python3 wifi_scanner_active.py --output file --file-path logs/perf_test.csv --continuous &
PID=$!
sleep 30
kill $PID
# Count unique scan_numbers in CSV
grep -v "scan_number" logs/perf_test.csv | cut -d',' -f2 | sort -u | wc -l
```

**Expected:** ~15-20 scans in 30 seconds (with 1.5s interval)

## Integration Test

Test with your fusion_logger workflow:

1. Run scanner and save to CSV
2. Verify CSV format matches what fusion_logger expects
3. Check timestamp format compatibility

```bash
sudo python3 wifi_scanner_active.py --output file --file-path logs/integration_test.csv --duration 10 --no-continuous
# Then test loading CSV in your fusion code
```

