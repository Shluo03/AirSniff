# AirSniff - WiFi Monitor Package TODO

## LEGEND
- [ ] TODO
- [P] In Progress
- [X] Completed
- [!] Blocked/Issue

---

## PHASE 1: ROS2 PACKAGE STRUCTURE & CONFIGURATION

### 1.1 Create ROS2 Package Skeleton
- [ ] Create `ros2_ws/src/wifi_monitor/` directory structure
- [ ] Create `package.xml` with dependencies:
  - rclpy (ROS2 Python client library)
  - std_msgs (for String message type)
  - geometry_msgs (if publishing position-tagged RSSI)
  - Custom message package (wifi_interfaces) - see 2.2
- [ ] Create `setup.py` with entry points for:
  - `wifi_scanner_node` (main node executable)
  - `wifi_test_node` (testing/debugging node)
- [ ] Create `resource/wifi_monitor` marker file (ROS2 requirement)
- [ ] Create directory structure:
  ```
  wifi_monitor/
  ├── package.xml
  ├── setup.py
  ├── resource/
  │   └── wifi_monitor
  ├── wifi_monitor/
  │   ├── __init__.py
  │   ├── wifi_scanner_node.py      # Main ROS2 node
  │   ├── packet_capture.py         # 802.11 frame capture logic
  │   ├── rssi_parser.py            # RadioTap header parsing
  │   ├── data_aggregator.py        # Aggregate RSSI per AP
  │   └── utils.py                  # Helper functions
  ├── config/
  │   └── wifi_params.yaml          # Node-specific parameters
  └── test/
      └── test_wifi_monitor.py      # Unit tests
  ```

### 1.2 Configuration File Schema
- [ ] Create `config/wifi_config.yaml` with structure:
  ```yaml
  wifi_monitor:
    ros__parameters:
      # Hardware Configuration
      interface: "wlan0"              # WiFi adapter interface name
      monitor_mode: true              # Enable monitor mode

      # Scanning Parameters
      scan_mode: "channel_hopping"    # Options: "channel_hopping", "fixed_channel"
      channels: [1, 6, 11]            # 2.4GHz channels to scan
      channel_dwell_time: 0.1         # Seconds per channel

      # RSSI Collection
      min_rssi: -90                   # Filter out weak signals (dBm)
      max_rssi: -20                   # Filter out anomalies (dBm)

      # ROS2 Publishing
      publish_rate: 10.0              # Hz (how often to publish aggregated data)
      topic_name: "/wifi/rssi"        # Output topic

      # Data Filtering
      target_bssids: []               # Empty = all APs, or specify MAC addresses
      ignore_hidden_ssids: false      # Skip APs with hidden SSIDs

      # Performance
      packet_buffer_size: 100         # Number of packets to buffer before processing
      enable_5ghz: false              # Scan 5GHz band (channels 36-165)
  ```

---

## PHASE 2: ROS2 MESSAGE DEFINITIONS

### 2.1 Decide on Message Format
- [ ] **Option A (Quick)**: Use `std_msgs/String` with JSON payload
  - Pros: No custom message compilation, faster iteration
  - Cons: Not type-safe, harder to debug

- [ ] **Option B (Recommended)**: Create custom message in `wifi_interfaces` package
  - Pros: Type-safe, proper ROS2 design, easier integration
  - Cons: Requires separate package, build step

### 2.2 Create Custom ROS2 Messages (if Option B)
- [ ] Create new package `ros2_ws/src/wifi_interfaces/`
- [ ] Define `msg/WifiScan.msg`:
  ```
  std_msgs/Header header          # Timestamp + frame_id
  WifiAP[] access_points          # Array of detected APs
  ```
- [ ] Define `msg/WifiAP.msg`:
  ```
  string bssid                    # MAC address (e.g., "AA:BB:CC:DD:EE:FF")
  string ssid                     # Network name (empty if hidden)
  int8 rssi                       # Signal strength in dBm (-90 to -20 typical)
  uint8 channel                   # WiFi channel number
  uint16 frequency                # Frequency in MHz (2412, 2437, etc.)
  string encryption               # "WPA2", "WPA3", "Open", etc.
  ```
- [ ] Build message package: `colcon build --packages-select wifi_interfaces`
- [ ] Update `wifi_monitor/package.xml` to depend on `wifi_interfaces`

### 2.3 JSON Schema (if using Option A)
- [ ] Document JSON format in README:
  ```json
  {
    "header": {
      "timestamp": 1234567890.123,
      "frame_id": "wifi_antenna"
    },
    "access_points": [
      {
        "bssid": "AA:BB:CC:DD:EE:FF",
        "ssid": "MyNetwork",
        "rssi": -45,
        "channel": 6,
        "frequency": 2437,
        "encryption": "WPA2"
      }
    ]
  }
  ```

---

## PHASE 3: 802.11 PACKET CAPTURE IMPLEMENTATION

### 3.1 WiFi Adapter Configuration
- [ ] Create `packet_capture.py::setup_monitor_mode()`:
  - [ ] Check if interface exists: `ip link show wlan0`
  - [ ] Bring interface down: `ip link set wlan0 down`
  - [ ] Set monitor mode: `iw dev wlan0 set monitor none`
  - [ ] Bring interface up: `ip link set wlan0 up`
  - [ ] Verify mode: `iwconfig wlan0` (should show "Mode:Monitor")
  - [ ] Handle errors (adapter not found, permissions, already in use)

- [ ] Create `packet_capture.py::restore_managed_mode()`:
  - [ ] Cleanup function to restore normal WiFi mode on node shutdown
  - [ ] Set back to managed mode: `iw dev wlan0 set type managed`

### 3.2 Channel Hopping Implementation
- [ ] Create `packet_capture.py::ChannelHopper` class:
  - [ ] Thread-safe channel switching
  - [ ] Use `iw dev wlan0 set channel X` to change channels
  - [ ] Implement dwell timer (sleep between channel changes)
  - [ ] Support both 2.4GHz and 5GHz channels
  - [ ] Log channel changes for debugging

### 3.3 Scapy Packet Capture
- [ ] Create `packet_capture.py::PacketCaptureThread` class:
  - [ ] Use `scapy.all.sniff()` with parameters:
    - `iface="wlan0"`
    - `prn=packet_callback` (callback function)
    - `store=False` (don't store in memory)
    - `monitor=True`
  - [ ] Filter for beacon frames and probe responses:
    - Filter: `type=0 subtype=8` (beacon) or `subtype=5` (probe response)
    - BPF filter: `"type mgt subtype beacon or subtype probe-resp"`

- [ ] Implement packet callback `packet_callback(pkt)`:
  - [ ] Check if packet has RadioTap layer: `pkt.haslayer(RadioTap)`
  - [ ] Check if packet has Dot11 layer: `pkt.haslayer(Dot11)`
  - [ ] Pass to RSSI parser (see Phase 4)

### 3.4 Error Handling & Permissions
- [ ] Check for root/sudo permissions before starting capture
- [ ] Handle `PermissionError` with helpful message
- [ ] Handle adapter disconnection gracefully
- [ ] Implement packet loss monitoring (count dropped packets)

---

## PHASE 4: RSSI EXTRACTION & PARSING

### 4.1 RadioTap Header Parsing
- [ ] Create `rssi_parser.py::extract_rssi(packet)`:
  - [ ] Extract RSSI from `packet[RadioTap].dBm_AntSignal`
  - [ ] Fallback to `packet[RadioTap].SignalLevel` if dBm not available
  - [ ] Handle missing RadioTap layer (return None)
  - [ ] Validate RSSI range (-90 to -20 dBm typical)

### 4.2 Access Point Information Extraction
- [ ] Create `rssi_parser.py::parse_wifi_packet(packet)` → returns dict:
  - [ ] Extract BSSID: `packet[Dot11].addr2` or `addr3` (transmitter address)
  - [ ] Extract SSID:
    - Parse `Dot11Elt` (802.11 Information Elements)
    - Find element with ID=0 (SSID)
    - Decode: `elt.info.decode('utf-8', errors='ignore')`
  - [ ] Extract channel:
    - Parse DS Parameter Set (Dot11Elt ID=3)
    - Or calculate from `packet[RadioTap].ChannelFrequency`
  - [ ] Extract encryption type:
    - Check for RSN (ID=48) → WPA2/WPA3
    - Check for Vendor Specific (ID=221) → WPA
    - Neither → Open
  - [ ] Return structured dict:
    ```python
    {
      'bssid': 'AA:BB:CC:DD:EE:FF',
      'ssid': 'NetworkName',
      'rssi': -45,
      'channel': 6,
      'frequency': 2437,
      'encryption': 'WPA2',
      'timestamp': time.time()
    }
    ```

### 4.3 Data Validation
- [ ] Create `rssi_parser.py::validate_ap_data(ap_dict)`:
  - [ ] Check BSSID format (valid MAC address)
  - [ ] Check RSSI in acceptable range
  - [ ] Check channel is valid (1-14 for 2.4GHz, 36-165 for 5GHz)
  - [ ] Sanitize SSID (remove non-printable characters)

---

## PHASE 5: DATA AGGREGATION

### 5.1 RSSI Averaging
- [ ] Create `data_aggregator.py::RSSIAggregator` class:
  - [ ] Maintain dictionary: `{bssid: [rssi_samples]}`
  - [ ] Add method `add_sample(bssid, rssi)`
  - [ ] Add method `get_average(bssid)` → returns mean RSSI
  - [ ] Implement sliding window (e.g., last 10 samples per AP)
  - [ ] Add timestamp tracking for each sample

### 5.2 Access Point State Management
- [ ] Track last seen time for each AP
- [ ] Remove stale APs (not seen in last N seconds)
- [ ] Handle SSID changes (some APs broadcast multiple SSIDs)
- [ ] Deduplicate entries (same BSSID seen on multiple channels)

### 5.3 Publication Buffering
- [ ] Create method `get_snapshot()` → returns all APs with averaged RSSI
- [ ] Clear/reset buffer after publishing (if needed)
- [ ] Handle empty buffer (no APs detected)

---

## PHASE 6: ROS2 NODE IMPLEMENTATION

### 6.1 Main Node Class
- [ ] Create `wifi_scanner_node.py::WifiScannerNode(Node)`:
  - [ ] Initialize ROS2 node: `super().__init__('wifi_scanner_node')`
  - [ ] Declare parameters from config:
    ```python
    self.declare_parameter('interface', 'wlan0')
    self.declare_parameter('publish_rate', 10.0)
    # ... etc
    ```
  - [ ] Create publisher:
    ```python
    self.publisher_ = self.create_publisher(
        String,  # or WifiScan if custom message
        '/wifi/rssi',
        10  # QoS queue size
    )
    ```
  - [ ] Create timer for periodic publishing:
    ```python
    self.timer = self.create_timer(
        1.0 / self.get_parameter('publish_rate').value,
        self.publish_callback
    )
    ```

### 6.2 Node Lifecycle Management
- [ ] Implement `__init__()`:
  - [ ] Load parameters
  - [ ] Initialize packet capture thread
  - [ ] Initialize RSSI aggregator
  - [ ] Setup monitor mode
  - [ ] Start channel hopper (if enabled)
  - [ ] Start packet capture
  - [ ] Log initialization status

- [ ] Implement `publish_callback()`:
  - [ ] Get snapshot from aggregator
  - [ ] Create ROS message (String/JSON or WifiScan)
  - [ ] Add timestamp header
  - [ ] Publish message
  - [ ] Log published AP count (for debugging)

- [ ] Implement `destroy_node()`:
  - [ ] Stop packet capture thread
  - [ ] Stop channel hopper
  - [ ] Restore managed mode
  - [ ] Cleanup resources
  - [ ] Call `super().destroy_node()`

### 6.3 Thread Safety
- [ ] Use `threading.Lock()` for shared data structures
- [ ] Ensure packet callback and publish callback don't race
- [ ] Handle ROS2 shutdown signals gracefully

### 6.4 Logging & Debugging
- [ ] Use ROS2 logger: `self.get_logger().info()`
- [ ] Log levels:
  - DEBUG: Individual packet details
  - INFO: Startup, AP count, publish events
  - WARN: Missing permissions, adapter issues
  - ERROR: Capture failures, parsing errors
- [ ] Add parameter for verbose logging

---

## PHASE 7: ROS2 INTEGRATION

### 7.1 Time Synchronization
- [ ] Use ROS2 time: `self.get_clock().now().to_msg()`
- [ ] Ensure WiFi timestamps match SLAM timestamps (same clock source)
- [ ] Handle clock skew between WiFi and SLAM nodes
- [ ] Add timestamp to every published message header

### 7.2 Frame ID Convention
- [ ] Set consistent frame_id in message header:
  - Option 1: `"wifi_antenna"` (if WiFi adapter is separate from camera)
  - Option 2: `"base_link"` (if mounted on drone body)
  - Option 3: `"drone_link"` (match SLAM frame)
- [ ] Document frame_id choice in config YAML

### 7.3 Message Publishing Strategy
- [ ] **Option A**: Publish all detected APs in single message (array)
  - Pros: Atomic snapshot, easier fusion
  - Cons: Large messages if many APs

- [ ] **Option B**: Publish individual AP messages
  - Pros: Lower latency, smaller messages
  - Cons: Harder to synchronize in fusion node

- [ ] Choose and implement (recommend Option A)

### 7.4 QoS Configuration
- [ ] Set appropriate QoS profile:
  - Reliability: RELIABLE (don't drop WiFi data)
  - Durability: VOLATILE (no need to persist)
  - History: KEEP_LAST with depth=10
- [ ] Test with `ros2 topic echo /wifi/rssi`

---

## PHASE 8: TESTING & VALIDATION

### 8.1 Unit Tests
- [ ] Test `rssi_parser.py`:
  - [ ] Mock Scapy packets with known RSSI values
  - [ ] Test SSID extraction (ASCII, UTF-8, hidden)
  - [ ] Test encryption detection
  - [ ] Test invalid packet handling

- [ ] Test `data_aggregator.py`:
  - [ ] Test RSSI averaging with known samples
  - [ ] Test stale AP removal
  - [ ] Test edge cases (empty buffer, single sample)

- [ ] Test `packet_capture.py`:
  - [ ] Test monitor mode setup (may need mock)
  - [ ] Test channel hopping sequence
  - [ ] Test graceful shutdown

### 8.2 Integration Tests
- [ ] Test ROS2 node standalone:
  ```bash
  ros2 run wifi_monitor wifi_scanner_node --ros-args --params-file config/wifi_config.yaml
  ```
- [ ] Verify publishing: `ros2 topic echo /wifi/rssi`
- [ ] Check message rate: `ros2 topic hz /wifi/rssi`
- [ ] Verify data quality:
  - [ ] RSSI values in expected range
  - [ ] Known APs detected
  - [ ] BSSID/SSID accuracy

### 8.3 Field Testing
- [ ] Test in controlled environment (known AP locations)
- [ ] Verify RSSI decreases with distance
- [ ] Test channel hopping coverage (all channels scanned)
- [ ] Test with drone movement (while SLAM is running)
- [ ] Measure packet capture rate (packets/sec)
- [ ] Monitor CPU/memory usage on Jetson

### 8.4 Performance Benchmarking
- [ ] Measure latency: packet capture → ROS publish
- [ ] Test with varying publish rates (1Hz, 10Hz, 20Hz)
- [ ] Test with varying number of APs (1, 10, 50+)
- [ ] Profile packet processing time
- [ ] Ensure real-time performance on Jetson

---

## PHASE 9: DOCUMENTATION

### 9.1 Code Documentation
- [ ] Add docstrings to all functions/classes (Google style)
- [ ] Add inline comments for complex logic (RadioTap parsing)
- [ ] Document assumptions (e.g., adapter supports monitor mode)

### 9.2 User Documentation
- [ ] Create `wifi_monitor/README.md`:
  - [ ] Package purpose
  - [ ] Dependencies
  - [ ] Hardware requirements (WiFi adapter models)
  - [ ] Configuration guide
  - [ ] Troubleshooting section

- [ ] Create setup guide for WiFi adapter:
  - [ ] Checking monitor mode support
  - [ ] Installing drivers (if needed)
  - [ ] Permission setup (udev rules to avoid sudo)

### 9.3 API Documentation
- [ ] Document published topics:
  - Topic name
  - Message type
  - Publish rate
  - Data format
- [ ] Document parameters (from config YAML)
- [ ] Document frame_id conventions

---

## PHASE 10: INTEGRATION WITH FUSION NODE

### 10.1 Coordinate with Fusion Team
- [ ] Confirm message format expectations
- [ ] Confirm timestamp synchronization approach
- [ ] Test message deserialization in fusion node
- [ ] Handle edge cases:
  - [ ] No APs detected (publish empty array?)
  - [ ] WiFi node startup delay
  - [ ] WiFi node crash recovery

### 10.2 End-to-End Testing
- [ ] Test full pipeline: Camera → SLAM → Pose + WiFi → Fusion → CSV
- [ ] Verify timestamps align in fused CSV log
- [ ] Verify RSSI values appear correctly in log
- [ ] Test with drone flight (static hover, slow movement, fast movement)

---

## PHASE 11: OPTIMIZATION & PRODUCTION READINESS

### 11.1 Performance Optimization
- [ ] Profile packet capture bottlenecks
- [ ] Optimize RSSI aggregation (use numpy for averaging?)
- [ ] Reduce ROS message serialization overhead
- [ ] Test on Jetson under load (SLAM + WiFi + other nodes)

### 11.2 Error Recovery
- [ ] Handle WiFi adapter hot-unplug/replug
- [ ] Auto-restart capture on failure
- [ ] Publish node health/status on separate topic
- [ ] Implement watchdog timer

### 11.3 Configuration Flexibility
- [ ] Support runtime parameter changes (ROS2 param server)
- [ ] Allow toggling channel hopping without restart
- [ ] Allow changing publish rate on-the-fly

### 11.4 Launch File Integration
- [ ] Add wifi_monitor node to `launch/mvp_system.launch.py`
- [ ] Set proper node namespace
- [ ] Pass config file path
- [ ] Set dependencies (SLAM node starts first?)

---

## DEPENDENCIES CHECKLIST

### System Dependencies (apt)
- [ ] `sudo apt install wireless-tools`
- [ ] `sudo apt install iw`
- [ ] `sudo apt install aircrack-ng` (optional, for testing)

### Python Dependencies (pip)
- [ ] `scapy>=2.5.0`
- [ ] `pandas>=2.0.0` (if doing complex aggregation)
- [ ] `numpy>=1.24.0` (for averaging)

### ROS2 Dependencies
- [ ] `rclpy`
- [ ] `std_msgs`
- [ ] `wifi_interfaces` (if custom messages)

---

## POTENTIAL ISSUES & SOLUTIONS

### Issue 1: Monitor Mode Not Working
- **Symptom**: `iw` command fails, or no packets captured
- **Solutions**:
  - [ ] Check adapter chipset compatibility (realtek, atheros, ralink)
  - [ ] Update kernel drivers
  - [ ] Try different adapter

### Issue 2: Permission Denied
- **Symptom**: Scapy fails with "Operation not permitted"
- **Solutions**:
  - [ ] Run node with sudo (not recommended for ROS2)
  - [ ] Set capabilities: `sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)`
  - [ ] Create udev rule for WiFi adapter

### Issue 3: No RSSI in Packets
- **Symptom**: `packet[RadioTap].dBm_AntSignal` is None
- **Solutions**:
  - [ ] Check if adapter exposes RSSI in radiotap
  - [ ] Try different adapter
  - [ ] Use alternative RSSI field (SignalLevel)

### Issue 4: High CPU Usage
- **Symptom**: Jetson CPU maxed out, node lags
- **Solutions**:
  - [ ] Reduce publish rate
  - [ ] Filter packets earlier (BPF filter)
  - [ ] Increase channel dwell time (scan slower)
  - [ ] Process packets in batches

### Issue 5: Timestamp Drift
- **Symptom**: WiFi and SLAM timestamps don't align
- **Solutions**:
  - [ ] Use ROS2 clock for all timestamps
  - [ ] Check NTP sync if using multiple devices
  - [ ] Add timestamp offset calibration

---

## MILESTONES

- [ ] **M1**: ROS2 package builds and runs (no packet capture yet)
- [ ] **M2**: Packet capture working, prints RSSI to terminal
- [ ] **M3**: RSSI publishing to ROS2 topic (single AP)
- [ ] **M4**: Multi-AP detection with channel hopping
- [ ] **M5**: Integration with fusion node, CSV logs generated
- [ ] **M6**: Field-tested on drone with SLAM running

---

## CURRENT STATUS
- Package: `wifi_monitor`
- Owner: [Your Name]
- Status: **NOT STARTED**
- Target Completion: [Set Date]
- Blockers: None

---

## NOTES
- Coordinate with SLAM team on timestamp sync strategy
- May need to purchase specific WiFi adapter if current one doesn't support monitor mode
- Consider using 2.4GHz only initially (better range, simpler), add 5GHz later
- Test on ground before drone flight (safety)
