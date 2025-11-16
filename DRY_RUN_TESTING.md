# Dry Run Testing Guide

## ✅ Dry Run Mode Available!

You can now test the WiFi scanner **on macOS** (or any system) without needing actual WiFi hardware or `sudo` permissions!

## Quick Start

### Test 1: Basic Dry Run (Console Output)
```bash
python3 wifi_scanner_active.py --dry-run --duration 5 --no-continuous
```
**What this tests:**
- ✅ Config file loading
- ✅ CLI argument parsing
- ✅ Console output formatting
- ✅ Timing and loop logic
- ✅ Exit handling

### Test 2: CSV Output (Dry Run)
```bash
python3 wifi_scanner_active.py --dry-run --output file --file-path logs/test.csv --duration 5 --no-continuous
cat logs/test.csv
```
**What this tests:**
- ✅ CSV file creation
- ✅ CSV header formatting
- ✅ CSV data rows
- ✅ Timestamp formatting
- ✅ All CSV columns (timestamp, scan_number, ssid, bssid, rssi, channel, quality)

### Test 3: Both Output (Dry Run)
```bash
python3 wifi_scanner_active.py --dry-run --output both --file-path logs/both_test.csv --duration 3 --no-continuous
```
**What this tests:**
- ✅ Simultaneous console and CSV output
- ✅ Both outputs work correctly

### Test 4: Continuous Mode (Dry Run)
```bash
python3 wifi_scanner_active.py --dry-run --continuous
# Press Ctrl+C after a few scans
```
**What this tests:**
- ✅ Continuous loop mode
- ✅ Ctrl+C handling
- ✅ Summary statistics on exit

### Test 5: CLI Overrides (Dry Run)
```bash
python3 wifi_scanner_active.py --dry-run --scan-interval 2.0 --output both --file-path logs/custom.csv --duration 10 --no-continuous
```
**What this tests:**
- ✅ CLI arguments override config file
- ✅ All config options work via CLI
- ✅ Merged configuration is correct

## What Dry Run Mode Does

1. **Skips WiFi interface validation** - No need for actual WiFi hardware
2. **Uses mock data** - Generates 6 sample WiFi networks with different RSSI values
3. **Tests all output paths** - Console, CSV, or both
4. **No sudo required** - Works without root permissions
5. **Full functionality testing** - Tests all code paths except actual WiFi scanning

## Mock Data Generated

Dry run mode creates these sample networks:
- `TestNetwork_Strong` (-45 dBm) - Excellent quality
- `TestNetwork_Good` (-55 dBm) - Good quality  
- `TestNetwork_Fair` (-65 dBm) - Fair quality
- `TestNetwork_Weak` (-75 dBm) - Weak quality
- `<Hidden Network>` (-80 dBm) - Weak quality
- `TestNetwork_VeryWeak` (-85 dBm) - Very Weak quality

This covers all RSSI ranges to test filtering and quality classification.

## Advantages

✅ **Test on macOS** - No need to wait for Jetson access  
✅ **No sudo needed** - Test without root permissions  
✅ **Fast iteration** - Test config changes quickly  
✅ **No hardware dependency** - Test even without WiFi adapter  
✅ **Full code path testing** - Test everything except actual scanning  

## What Still Needs Jetson

After dry-run testing, you'll still need to test on Jetson for:
- Actual WiFi scanning functionality
- Real RSSI values from your environment
- Performance with real WiFi hardware
- Integration with actual drone hardware

## Example Workflow

1. **On macOS (dry-run):**
   ```bash
   # Test configuration
   python3 wifi_scanner_active.py --dry-run --duration 5 --no-continuous
   
   # Test CSV output
   python3 wifi_scanner_active.py --dry-run --output file --duration 5 --no-continuous
   
   # Test different configs
   python3 wifi_scanner_active.py --dry-run --scan-interval 2.0 --output both
   ```

2. **On Jetson (actual scanning):**
   ```bash
   # Real scanning with same config
   sudo python3 wifi_scanner_active.py --duration 5 --no-continuous
   
   # Production run
   sudo python3 wifi_scanner_active.py --continuous
   ```

## Tips

- Use `--duration 3 --no-continuous` for quick tests
- Check CSV files to verify output format
- Test all CLI arguments with `--dry-run` first
- Use dry-run to verify config file changes work
- Test error handling (invalid paths, etc.) with dry-run

