# WiFi Scanner Configuration Implementation TODO

**Goal:** Make `wifi_scanner_active.py` configurable with YAML config file + CLI arguments, continuous loop, and multiple output formats.

**Status:** Not Started
**Target:** Complete all phases

---

## PHASE 1: SETUP & DIRECTORY STRUCTURE

### 1.1 Create Directory Structure
- [ ] Create `config/` directory in project root
- [ ] Create `logs/` directory in project root
- [ ] Create `logs/.gitkeep` file (to keep directory in git)
- [ ] Verify directory structure exists

### 1.2 Verify Dependencies
- [ ] Check PyYAML is installed: `python3 -c "import yaml; print(yaml.__version__)"`
- [ ] Verify argparse is available (built-in, no check needed)
- [ ] Verify csv module is available (built-in, no check needed)
- [ ] If PyYAML missing, install: `pip install pyyaml` (in venv)

---

## PHASE 2: CREATE DEFAULT CONFIGURATION FILE

### 2.1 Create YAML Config File
- [ ] Create `config/wifi_config.yaml` file
- [ ] Add top-level `wifi_scanner:` key
- [ ] Add `interface: "wlP1p1s0"` (hardware config)
- [ ] Add `scan_method: "iwlist"` (scanning parameters)
- [ ] Add `scan_interval: 1.5` (scanning parameters)
- [ ] Add `continuous: true` (runtime mode)
- [ ] Add `duration: 30` (runtime mode, for non-continuous)
- [ ] Add `output:` section with:
  - [ ] `console: true`
  - [ ] `file: false`
  - [ ] `file_path: "logs/wifi_scans.csv"`
- [ ] Add `filters:` section with:
  - [ ] `min_rssi: -90`
  - [ ] `max_rssi: -20`
- [ ] Validate YAML syntax (no tabs, proper indentation)
- [ ] Test loading: `python3 -c "import yaml; print(yaml.safe_load(open('config/wifi_config.yaml')))"`

---

## PHASE 3: ADD IMPORTS & CONFIGURATION LOADING

### 3.1 Add Required Imports
- [ ] Add `import yaml` at top of `wifi_scanner_active.py`
- [ ] Add `import argparse` at top of `wifi_scanner_active.py`
- [ ] Add `import csv` at top of `wifi_scanner_active.py`
- [ ] Add `import os` at top of `wifi_scanner_active.py` (for path operations)
- [ ] Add `from pathlib import Path` at top (for path handling)

### 3.2 Implement Config Loading Function
- [ ] Create function `load_config(config_path: str) -> dict:`
- [ ] Add docstring explaining function purpose
- [ ] Add try/except for file not found
- [ ] Add try/except for YAML parsing errors
- [ ] Return default config dict if file not found (with warning)
- [ ] Return parsed config dict if successful
- [ ] Extract `wifi_scanner` key from loaded YAML
- [ ] Test function with valid config file
- [ ] Test function with missing config file
- [ ] Test function with invalid YAML

### 3.3 Implement CLI Argument Parser
- [ ] Create function `parse_cli_args() -> argparse.Namespace:`
- [ ] Add docstring explaining function purpose
- [ ] Initialize `argparse.ArgumentParser` with description
- [ ] Add `--config, -c` argument (default: "config/wifi_config.yaml")
- [ ] Add `--interface, -i` argument (help: "WiFi interface name")
- [ ] Add `--output, -o` argument (choices: ["console", "file", "both"])
- [ ] Add `--file-path, -f` argument (help: "Output file path")
- [ ] Add `--scan-interval, -s` argument (type=float, help: "Seconds between scans")
- [ ] Add `--continuous` argument (action="store_true", help: "Run continuously")
- [ ] Add `--no-continuous` argument (action="store_false", dest="continuous")
- [ ] Add `--duration, -d` argument (type=int, help: "Duration in seconds")
- [ ] Add `--scan-method` argument (choices: ["iwlist", "nmcli"])
- [ ] Return parsed args
- [ ] Test parser with `--help` flag
- [ ] Test parser with various argument combinations

### 3.4 Implement Config Merging Function
- [ ] Create function `merge_config(config_dict: dict, cli_args: argparse.Namespace) -> dict:`
- [ ] Add docstring explaining merge priority (CLI > YAML > defaults)
- [ ] Create merged config dict (start with YAML config)
- [ ] Override `interface` if `cli_args.interface` is not None
- [ ] Override `scan_method` if `cli_args.scan_method` is not None
- [ ] Override `scan_interval` if `cli_args.scan_interval` is not None
- [ ] Override `continuous` if `cli_args.continuous` is not None
- [ ] Override `duration` if `cli_args.duration` is not None
- [ ] Handle `output` override (parse "console"/"file"/"both" to boolean flags)
- [ ] Override `file_path` if `cli_args.file_path` is not None
- [ ] Return merged config dict
- [ ] Test merge with all CLI args set
- [ ] Test merge with no CLI args (YAML only)
- [ ] Test merge with partial CLI args

---

## PHASE 4: IMPLEMENT CONFIGURATION VALIDATION

### 4.1 Create Validation Function
- [ ] Create function `validate_config(config: dict) -> bool:`
- [ ] Add docstring explaining validation checks
- [ ] Check `interface` exists: run `ip link show <interface>` or check `/sys/class/net/`
- [ ] Validate `scan_interval > 0` (raise ValueError if invalid)
- [ ] Validate `scan_method` is "iwlist" or "nmcli"
- [ ] If `output.file` is True:
  - [ ] Extract directory from `file_path`
  - [ ] Check if directory exists, create if not
  - [ ] Check if directory is writable
- [ ] Validate `filters.min_rssi < filters.max_rssi`
- [ ] Validate `duration > 0` if `continuous` is False
- [ ] Return True if all validations pass
- [ ] Raise appropriate exceptions with clear error messages
- [ ] Test validation with valid config
- [ ] Test validation with invalid interface
- [ ] Test validation with invalid scan_interval
- [ ] Test validation with non-writable file path

---

## PHASE 5: IMPLEMENT OUTPUT HANDLERS

**Note:** We're implementing CSV output only (matches fusion_logger workflow). JSON can be added later if needed.

**Flow:**
```
main() 
  → write_output(networks, config, ...)
    → if console: print_console_output()
    → if file: write_csv_output()
```

### 5.1 Refactor Console Output
- [ ] Create function `print_console_output(networks: list, scan_number: int, timestamp: str) -> None:`
- [ ] Move existing print logic from `main()` to this function
- [ ] Add docstring
- [ ] Keep existing format (scan header, network list)
- [ ] Sort networks by RSSI (strongest first)
- [ ] Handle empty networks list (print "No networks found")
- [ ] Test function with sample network data
- [ ] Test function with empty list

### 5.2 Implement CSV Output Function
**Purpose:** Write scan data to CSV file format. Matches fusion_logger CSV format for easy integration.
- [ ] Create function `write_csv_output(networks: list, file_path: str, scan_number: int, timestamp: datetime) -> None:`
- [ ] Add docstring explaining CSV format
- [ ] Check if file exists (to write header on first write)
- [ ] Open file in append mode ('a')
- [ ] Create CSV writer
- [ ] Write header row if new file: `timestamp,scan_number,ssid,bssid,rssi,channel,quality`
- [ ] For each network, write row with all fields
- [ ] Handle file write errors (permissions, disk full)
- [ ] Close file properly
- [ ] Test with new file (header written)
- [ ] Test with existing file (append mode)
- [ ] Test with multiple scans (multiple rows)
- [ ] Verify CSV format is correct

### 5.3 Create Output Router Function
**Purpose:** Routes output to console and/or CSV file based on config.
- [ ] Create function `write_output(networks: list, config: dict, scan_number: int, timestamp: datetime) -> None:`
- [ ] Add docstring explaining routing logic
- [ ] Check `config['output']['console']` and call `print_console_output()` if True
- [ ] Check `config['output']['file']` and call `write_csv_output()` if True
- [ ] Handle errors from output functions gracefully
- [ ] Test with console only (no file output)
- [ ] Test with CSV file only (no console)
- [ ] Test with both console and CSV file

---

## PHASE 6: IMPLEMENT DATA FILTERING

### 6.1 Add Filter Function
- [ ] Create function `filter_networks(networks: list, config: dict) -> list:`
- [ ] Add docstring explaining filtering logic
- [ ] Filter by `min_rssi` (exclude networks with RSSI < min_rssi)
- [ ] Filter by `max_rssi` (exclude networks with RSSI > max_rssi)
- [ ] Return filtered list
- [ ] Test with networks above/below thresholds
- [ ] Test with empty filters (all pass through)

---

## PHASE 7: REFACTOR MAIN FUNCTION

### 7.1 Update Main Function Structure
- [ ] Load config: call `load_config()` with default or CLI-specified path
- [ ] Parse CLI args: call `parse_cli_args()`
- [ ] Merge configs: call `merge_config(config, cli_args)`
- [ ] Validate config: call `validate_config(merged_config)`
- [ ] Extract values from merged config to local variables:
  - [ ] `interface = config['interface']`
  - [ ] `scan_method = config['scan_method']`
  - [ ] `scan_interval = config['scan_interval']`
  - [ ] `continuous = config['continuous']`
  - [ ] `duration = config.get('duration', 30)`
- [ ] Update startup banner to show configuration:
  - [ ] Show interface name
  - [ ] Show scan method
  - [ ] Show scan interval
  - [ ] Show runtime mode (continuous vs timed)
  - [ ] Show output destinations

### 7.2 Implement Continuous Loop
- [ ] Replace fixed 30-second loop with conditional:
  - [ ] If `continuous == True`: use `while True:` loop
  - [ ] If `continuous == False`: use timed loop `while (time.time() - start_time) < duration:`
- [ ] Initialize `scan_count = 0` before loop
- [ ] Inside loop:
  - [ ] Increment `scan_count`
  - [ ] Get current timestamp: `datetime.now()`
  - [ ] Perform scan (call `scan_wifi_iwlist()` or `scan_wifi_nmcli()`)
  - [ ] Filter networks: call `filter_networks(networks, config)`
  - [ ] Write output: call `write_output(networks, config, scan_count, timestamp)`
  - [ ] Sleep for `scan_interval` seconds
- [ ] Test continuous mode (Ctrl+C to stop)
- [ ] Test timed mode (runs for specified duration)

### 7.3 Update Error Handling
- [ ] Wrap config loading in try/except (file errors)
- [ ] Wrap validation in try/except (validation errors)
- [ ] Keep existing PermissionError handling
- [ ] Keep existing KeyboardInterrupt handling
- [ ] Add exception handling for file write errors
- [ ] Add exception handling for config merge errors
- [ ] Print helpful error messages for each exception type

### 7.4 Add Cleanup Logic
- [ ] Add cleanup section in KeyboardInterrupt handler
- [ ] Add cleanup section in exception handler
- [ ] Print summary statistics:
  - [ ] Total scans performed
  - [ ] Total networks detected
  - [ ] Output file location (if file output enabled)
- [ ] Test cleanup on normal exit
- [ ] Test cleanup on Ctrl+C
- [ ] Test cleanup on error

---

## PHASE 8: TESTING & VALIDATION

### 8.1 Test Default Configuration
- [ ] Run: `sudo python3 wifi_scanner_active.py`
- [ ] Verify uses `config/wifi_config.yaml`
- [ ] Verify runs continuously
- [ ] Verify console output works
- [ ] Verify interface is correct
- [ ] Verify scan interval is correct
- [ ] Stop with Ctrl+C, verify cleanup message

### 8.2 Test CLI Overrides
- [ ] Test: `sudo python3 wifi_scanner_active.py --interface wlan0`
- [ ] Verify interface override works
- [ ] Test: `sudo python3 wifi_scanner_active.py --scan-interval 2.0`
- [ ] Verify scan interval override works
- [ ] Test: `sudo python3 wifi_scanner_active.py --output file --file-path logs/test.csv`
- [ ] Verify file output works
- [ ] Test: `sudo python3 wifi_scanner_active.py --output both`
- [ ] Verify both console and CSV file output
- [ ] Test: `sudo python3 wifi_scanner_active.py --duration 10 --no-continuous`
- [ ] Verify timed mode works

### 8.3 Test File Output Formats
- [ ] Run scanner with CSV output for 3 scans
- [ ] Verify `logs/wifi_scans.csv` exists
- [ ] Verify CSV has correct header
- [ ] Verify CSV has 3 data rows (one per scan)
- [ ] Verify all columns present (timestamp, ssid, bssid, rssi, etc.)

### 8.4 Test Error Handling
- [ ] Test with invalid interface: `--interface invalid0`
- [ ] Verify clear error message
- [ ] Test with invalid config file: `--config nonexistent.yaml`
- [ ] Verify falls back to defaults with warning
- [ ] Test with invalid YAML in config file
- [ ] Verify clear error message
- [ ] Test with non-writable file path: `--file-path /root/test.csv`
- [ ] Verify clear error message
- [ ] Test with invalid scan_interval: `--scan-interval -1`
- [ ] Verify validation catches it

### 8.5 Test Filtering
- [ ] Set `min_rssi: -70` in config
- [ ] Run scanner
- [ ] Verify only networks with RSSI >= -70 are shown
- [ ] Set `max_rssi: -50` in config
- [ ] Run scanner
- [ ] Verify only networks with RSSI <= -50 are shown

### 8.6 Integration Test
- [ ] Run continuous scan for 30 seconds
- [ ] Verify console output is readable
- [ ] Verify file output (if enabled) is correct
- [ ] Verify no crashes or errors
- [ ] Verify Ctrl+C stops gracefully
- [ ] Verify summary statistics printed

---

## PHASE 9: DOCUMENTATION & CLEANUP

### 9.1 Update Code Documentation
- [ ] Add module-level docstring to `wifi_scanner_active.py`
- [ ] Ensure all functions have docstrings
- [ ] Add inline comments for complex logic
- [ ] Document config file format in code comments
- [ ] Document CLI arguments in code comments

### 9.2 Update README
- [ ] Add section "Configuration" to README.md
- [ ] Document config file location and format
- [ ] Document CLI arguments with examples
- [ ] Add usage examples:
  - [ ] Basic usage (default config)
  - [ ] Override interface
  - [ ] Save to file
  - [ ] Continuous vs timed mode
- [ ] Document CSV output format
- [ ] Add troubleshooting section for common errors

### 9.3 Create Example Config Files
- [ ] Create `config/wifi_config.example.yaml` (template)
- [ ] Add comments explaining each option
- [ ] Document valid values for each field
- [ ] Add example for different use cases

### 9.4 Update .gitignore
- [ ] Add `logs/*.csv` to .gitignore
- [ ] Keep `logs/.gitkeep` in git
- [ ] Verify logs directory structure is preserved

---

## PHASE 10: FINAL VERIFICATION

### 10.1 Code Review Checklist
- [ ] All functions have docstrings
- [ ] All error cases handled
- [ ] No hardcoded values (except defaults)
- [ ] Code follows existing style
- [ ] No unused imports
- [ ] All TODO comments addressed

### 10.2 Functionality Checklist
- [ ] Default config works
- [ ] CLI overrides work
- [ ] Continuous mode works
- [ ] Timed mode works
- [ ] Console output works
- [ ] CSV output works
- [ ] Filtering works
- [ ] Error handling works
- [ ] Cleanup works

### 10.3 Performance Check
- [ ] Scanner runs without performance degradation
- [ ] File I/O doesn't block scanning
- [ ] Memory usage is reasonable
- [ ] No memory leaks in continuous mode

### 10.4 User Experience Check
- [ ] Error messages are clear and helpful
- [ ] Startup banner shows useful info
- [ ] Output is readable and formatted well
- [ ] Ctrl+C stops gracefully
- [ ] Summary statistics are useful

---

## COMPLETION CRITERIA

**Project is complete when:**
- [ ] All TODO items above are checked
- [ ] Scanner runs with default config without errors
- [ ] All CLI arguments work as expected
- [ ] Continuous and timed modes both work
- [ ] Error handling is robust
- [ ] Documentation is updated
- [ ] Code is tested and verified

---

## NOTES

- Test on Jetson hardware (not just local machine)
- Verify sudo permissions work correctly
- Consider adding `--verbose` flag for debug output
- Consider adding `--quiet` flag to suppress console output
- Future: Consider adding `--filter-ssid` and `--filter-bssid` CLI args
- Future: Consider adding real-time statistics (APs/sec, avg RSSI, etc.)

---

**Last Updated:** [Date]
**Status:** Not Started
**Estimated Time:** 4-6 hours

