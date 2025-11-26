#!/usr/bin/env python3
"""
WiFi Scanner - Active Scanning Version
=======================================
This version uses ACTIVE scanning (works without monitor mode).

IMPORTANT DIFFERENCES from passive monitor mode:
- Uses iwlist/nmcli to actively request WiFi scans
- Scans every 1-2 seconds (vs continuous passive scanning)
- Works with built-in WiFi adapters (no monitor mode needed)
- Less frequent updates (acceptable for slow-moving or stationary scanning)

Use this version if:
- Your WiFi adapter doesn't support monitor mode
- You're doing stationary RF measurements
- You're learning WiFi concepts before getting proper hardware

For production drone RF heatmapping:
- You'll eventually need a WiFi adapter with monitor mode support
- See SETUP_INSTRUCTIONS.md for recommended adapters
"""

import subprocess
import re
import time
import sys
import os
import csv
import yaml
import argparse
from datetime import datetime
from pathlib import Path

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
RESET = '\033[0m'

def get_signal_quality(rssi):
    """
    Convert RSSI to human-readable quality.

    RSSI ranges:
    -30 to -50 dBm = Excellent
    -50 to -60 dBm = Good
    -60 to -70 dBm = Fair
    -70 to -80 dBm = Weak
    -80 to -90 dBm = Very Weak
    """
    if rssi >= -50:
        return f"{GREEN}Excellent{RESET}"
    elif rssi >= -60:
        return f"{GREEN}Good{RESET}"
    elif rssi >= -70:
        return f"{YELLOW}Fair{RESET}"
    elif rssi >= -80:
        return f"{YELLOW}Weak{RESET}"
    else:
        return f"{RED}Very Weak{RESET}"

def load_config(config_path):
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        dict: Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    default_config = {
        'interface': 'wlP1p1s0',
        'scan_method': 'iwlist',
        'scan_interval': 1.5,
        'continuous': True,
        'duration': 30,
        'output': {
            'console': True,
            'file': False,
            'file_path': 'logs/wifi_scans.csv'
        },
        'filters': {
            'min_rssi': -90,
            'max_rssi': -20
        }
    }
    
    try:
        with open(config_path, 'r') as f:
            loaded = yaml.safe_load(f)
            if loaded and 'wifi_scanner' in loaded:
                return loaded['wifi_scanner']
            else:
                print(f"{YELLOW}Warning: Invalid config file structure, using defaults{RESET}")
                return default_config
    except FileNotFoundError:
        print(f"{YELLOW}Warning: Config file '{config_path}' not found, using defaults{RESET}")
        return default_config
    except yaml.YAMLError as e:
        print(f"{RED}Error: Invalid YAML in config file: {e}{RESET}")
        print(f"{YELLOW}Using default configuration{RESET}")
        return default_config

def parse_cli_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='WiFi Scanner - Active Scanning Mode',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config/wifi_config.yaml',
        help='Path to YAML config file (default: config/wifi_config.yaml)'
    )
    parser.add_argument(
        '--interface', '-i',
        type=str,
        default=None,
        help='WiFi interface name (overrides config)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        choices=['console', 'file', 'both'],
        default=None,
        help='Output destination: console, file, or both (overrides config)'
    )
    parser.add_argument(
        '--file-path', '-f',
        type=str,
        default=None,
        help='Output file path (overrides config)'
    )
    parser.add_argument(
        '--scan-interval', '-s',
        type=float,
        default=None,
        help='Seconds between scans (overrides config)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        default=None,
        help='Run continuously until Ctrl+C (overrides config)'
    )
    parser.add_argument(
        '--no-continuous',
        action='store_false',
        dest='continuous',
        help='Run for fixed duration (overrides config)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=None,
        help='Duration in seconds (only if not continuous)'
    )
    parser.add_argument(
        '--scan-method',
        type=str,
        choices=['iwlist', 'nmcli'],
        default=None,
        help='Scan method: iwlist or nmcli (overrides config)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Dry run mode: test configuration without actual WiFi scanning (uses mock data)'
    )
    
    return parser.parse_args()

def merge_config(config_dict, cli_args):
    """
    Merge YAML config with CLI arguments.
    Priority: CLI args > YAML config > defaults
    
    Args:
        config_dict: Configuration from YAML file
        cli_args: Parsed CLI arguments
        
    Returns:
        dict: Merged configuration
    """
    merged = config_dict.copy()
    
    if cli_args.interface is not None:
        merged['interface'] = cli_args.interface
    
    if cli_args.scan_method is not None:
        merged['scan_method'] = cli_args.scan_method
    
    if cli_args.scan_interval is not None:
        merged['scan_interval'] = cli_args.scan_interval
    
    if cli_args.continuous is not None:
        merged['continuous'] = cli_args.continuous
    
    if cli_args.duration is not None:
        merged['duration'] = cli_args.duration
    
    if cli_args.output is not None:
        if cli_args.output == 'console':
            merged['output']['console'] = True
            merged['output']['file'] = False
        elif cli_args.output == 'file':
            merged['output']['console'] = False
            merged['output']['file'] = True
        elif cli_args.output == 'both':
            merged['output']['console'] = True
            merged['output']['file'] = True
    
    if cli_args.file_path is not None:
        merged['output']['file_path'] = cli_args.file_path
    
    return merged

def generate_mock_networks():
    """
    Generate mock WiFi network data for dry-run testing.
    
    Returns:
        list: List of mock network dictionaries
    """
    mock_networks = [
        {
            'ssid': 'TestNetwork_Strong',
            'bssid': 'AA:BB:CC:DD:EE:01',
            'rssi': -45,
            'channel': 6,
            'quality': get_signal_quality(-45)
        },
        {
            'ssid': 'TestNetwork_Good',
            'bssid': 'AA:BB:CC:DD:EE:02',
            'rssi': -55,
            'channel': 11,
            'quality': get_signal_quality(-55)
        },
        {
            'ssid': 'TestNetwork_Fair',
            'bssid': 'AA:BB:CC:DD:EE:03',
            'rssi': -65,
            'channel': 1,
            'quality': get_signal_quality(-65)
        },
        {
            'ssid': 'TestNetwork_Weak',
            'bssid': 'AA:BB:CC:DD:EE:04',
            'rssi': -75,
            'channel': 9,
            'quality': get_signal_quality(-75)
        },
        {
            'ssid': '<Hidden Network>',
            'bssid': 'AA:BB:CC:DD:EE:05',
            'rssi': -80,
            'channel': 3,
            'quality': get_signal_quality(-80)
        },
        {
            'ssid': 'TestNetwork_VeryWeak',
            'bssid': 'AA:BB:CC:DD:EE:06',
            'rssi': -85,
            'channel': 6,
            'quality': get_signal_quality(-85)
        }
    ]
    return mock_networks

def validate_config(config, dry_run=False):
    """
    Validate configuration parameters.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, skip interface validation
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If validation fails
        OSError: If interface doesn't exist or paths are invalid
    """
    # Check interface exists (skip in dry-run mode)
    if not dry_run:
        interface = config.get('interface')
        if not os.path.exists(f'/sys/class/net/{interface}'):
            raise OSError(f"WiFi interface '{interface}' does not exist. Check with: ip link show")
    
    # Validate scan_interval
    scan_interval = config.get('scan_interval', 1.5)
    if scan_interval <= 0:
        raise ValueError(f"scan_interval must be > 0, got {scan_interval}")
    
    # Validate scan_method
    scan_method = config.get('scan_method', 'iwlist')
    if scan_method not in ['iwlist', 'nmcli']:
        raise ValueError(f"scan_method must be 'iwlist' or 'nmcli', got '{scan_method}'")
    
    # Validate duration if not continuous
    if not config.get('continuous', True):
        duration = config.get('duration', 30)
        if duration <= 0:
            raise ValueError(f"duration must be > 0, got {duration}")
    
    # Validate file output
    if config.get('output', {}).get('file', False):
        file_path = config.get('output', {}).get('file_path', 'logs/wifi_scans.csv')
        file_dir = os.path.dirname(file_path)
        if file_dir:
            os.makedirs(file_dir, exist_ok=True)
            if not os.access(file_dir, os.W_OK):
                raise OSError(f"Cannot write to directory '{file_dir}'. Check permissions.")
    
    # Validate filters
    filters = config.get('filters', {})
    min_rssi = filters.get('min_rssi', -90)
    max_rssi = filters.get('max_rssi', -20)
    if min_rssi >= max_rssi:
        raise ValueError(f"min_rssi ({min_rssi}) must be < max_rssi ({max_rssi})")
    
    return True

def filter_networks(networks, config):
    """
    Filter networks based on configuration.
    
    Args:
        networks: List of network dictionaries
        config: Configuration dictionary
        
    Returns:
        list: Filtered networks
    """
    filters = config.get('filters', {})
    min_rssi = filters.get('min_rssi', -90)
    max_rssi = filters.get('max_rssi', -20)
    
    filtered = []
    for net in networks:
        rssi = net.get('rssi', -100)
        if min_rssi <= rssi <= max_rssi:
            filtered.append(net)
    
    return filtered

def print_console_output(networks, scan_number, timestamp):
    """
    Print scan results to console.
    
    Args:
        networks: List of network dictionaries
        scan_number: Current scan number
        timestamp: Current timestamp string
    """
    print(f"\n{CYAN}[Scan #{scan_number} at {timestamp}]{RESET}")
    print("-" * 80)
    
    if not networks:
        print(f"{YELLOW}No networks found in this scan{RESET}")
    else:
        # Sort by signal strength (strongest first)
        networks.sort(key=lambda x: x.get('rssi', -100), reverse=True)
        
        for net in networks:
            ssid = net.get('ssid', 'Unknown')
            bssid = net.get('bssid', 'Unknown')
            rssi = net.get('rssi', 0)
            quality = net.get('quality', 'Unknown')
            
            print(f"Network: {ssid:25s} | BSSID: {bssid:17s} | "
                  f"RSSI: {rssi:3d} dBm | Quality: {quality}")

def write_csv_output(networks, file_path, scan_number, timestamp):
    """
    Write scan results to CSV file.
    
    Args:
        networks: List of network dictionaries
        file_path: Path to CSV file
        scan_number: Current scan number
        timestamp: Current datetime object
    """
    file_exists = os.path.exists(file_path)
    
    try:
        file_dir = os.path.dirname(file_path)
        if file_dir:
            os.makedirs(file_dir, exist_ok=True)
        
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if new file
            if not file_exists:
                writer.writerow(['timestamp', 'scan_number', 'ssid', 'bssid', 'rssi', 'channel', 'quality'])
            
            # Write data rows
            for net in networks:
                writer.writerow([
                    timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    scan_number,
                    net.get('ssid', 'Unknown'),
                    net.get('bssid', 'Unknown'),
                    net.get('rssi', 0),
                    net.get('channel', '?'),
                    net.get('quality', 'Unknown').replace(RESET, '').replace(GREEN, '').replace(YELLOW, '').replace(RED, '')
                ])
    except IOError as e:
        print(f"{RED}Error writing to CSV file: {e}{RESET}")
        print(f"{YELLOW}File path: {file_path}{RESET}")
        print(f"{YELLOW}Directory exists: {os.path.exists(file_dir) if file_dir else 'N/A'}{RESET}")
    except Exception as e:
        print(f"{RED}Unexpected error writing CSV: {e}{RESET}")
        print(f"{YELLOW}File path: {file_path}{RESET}")

def write_output(networks, config, scan_number, timestamp):
    """
    Route output to console and/or CSV file based on config.
    
    Args:
        networks: List of network dictionaries
        config: Configuration dictionary
        scan_number: Current scan number
        timestamp: Current datetime object
    """
    output_config = config.get('output', {})
    
    # Console output
    if output_config.get('console', True):
        timestamp_str = timestamp.strftime("%H:%M:%S")
        print_console_output(networks, scan_number, timestamp_str)
    
    # File output
    if output_config.get('file', False):
        file_path = output_config.get('file_path', 'logs/wifi_scans.csv')
        write_csv_output(networks, file_path, scan_number, timestamp)
    else:
        if scan_number == 1:
            print(f"{YELLOW}Note: File output is disabled. Use --output file or --output both to enable CSV output.{RESET}")

def scan_wifi_iwlist(interface):
    """
    Scan WiFi networks using iwlist (active scanning).

    Returns list of dicts with network info:
    [
        {
            'ssid': 'NetworkName',
            'bssid': 'AA:BB:CC:DD:EE:FF',
            'rssi': -45,
            'channel': 6,
            'quality': 'Excellent'
        },
        ...
    ]
    """
    try:
        # Run iwlist scan
        result = subprocess.run(
            ['sudo', 'iwlist', interface, 'scan'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"{RED}Error running iwlist: {result.stderr}{RESET}")
            return []

        # Parse the output
        networks = []
        current_network = {}

        for line in result.stdout.split('\n'):
            line = line.strip()

            # New cell = new network
            if 'Cell' in line and 'Address:' in line:
                if current_network:
                    networks.append(current_network)
                current_network = {}
                # Extract BSSID
                match = re.search(r'Address: ([0-9A-Fa-f:]{17})', line)
                if match:
                    current_network['bssid'] = match.group(1)

            # Extract SSID
            elif 'ESSID:' in line:
                match = re.search(r'ESSID:"([^"]*)"', line)
                if match:
                    ssid = match.group(1)
                    current_network['ssid'] = ssid if ssid else '<Hidden Network>'

            # Extract Channel
            elif 'Channel:' in line or 'Frequency:' in line:
                match = re.search(r'Channel:?(\d+)', line)
                if match:
                    current_network['channel'] = int(match.group(1))

            # Extract Signal Level (RSSI)
            elif 'Signal level=' in line:
                # Format: "Signal level=-45 dBm" or "Signal level=65/100"
                match = re.search(r'Signal level=(-?\d+)', line)
                if match:
                    rssi = int(match.group(1))
                    # If value is positive (like 65/100), convert to dBm estimate
                    if rssi > 0:
                        # Rough conversion: 0-100 scale to -100 to -50 dBm
                        rssi = -100 + (rssi / 2)
                    current_network['rssi'] = int(rssi)
                    current_network['quality'] = get_signal_quality(rssi)

        # Add last network
        if current_network:
            networks.append(current_network)

        return networks

    except subprocess.TimeoutExpired:
        print(f"{RED}Scan timeout - WiFi might be busy{RESET}")
        return []
    except Exception as e:
        print(f"{RED}Error scanning: {e}{RESET}")
        return []

def scan_wifi_nmcli(interface):
    """
    Alternative: Scan using nmcli (NetworkManager).
    Often faster than iwlist.
    """
    try:
        # Trigger rescan
        subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'],
                      capture_output=True, timeout=5)

        # Get results
        result = subprocess.run(
            ['nmcli', '-f', 'SSID,BSSID,CHAN,SIGNAL', 'dev', 'wifi', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return []

        networks = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header

        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                # Parse: SSID BSSID CHAN SIGNAL
                ssid = parts[0] if parts[0] != '--' else '<Hidden Network>'
                bssid = parts[1] if ':' in parts[1] else parts[2]

                # Find signal (last numeric value)
                signal = None
                for part in reversed(parts):
                    if part.isdigit():
                        signal = int(part)
                        break

                if signal is not None:
                    # nmcli returns 0-100, convert to dBm estimate
                    rssi = -100 + (signal / 2)
                    networks.append({
                        'ssid': ssid,
                        'bssid': bssid,
                        'rssi': int(rssi),
                        'quality': get_signal_quality(rssi)
                    })

        return networks

    except Exception as e:
        return []

def main():
    """
    Main function - active WiFi scanner.
    """
    # Load and parse configuration
    cli_args = parse_cli_args()
    dry_run = cli_args.dry_run
    config_dict = load_config(cli_args.config)
    config = merge_config(config_dict, cli_args)
    
    # Validate configuration (skip interface check in dry-run mode)
    try:
        validate_config(config, dry_run=dry_run)
    except (ValueError, OSError) as e:
        print(f"{RED}❌ Configuration Error: {e}{RESET}")
        sys.exit(1)
    
    # Extract configuration values
    interface = config['interface']
    scan_method = config['scan_method']
    scan_interval = config['scan_interval']
    continuous = config['continuous']
    duration = config.get('duration', 30)
    
    # Print startup banner
    print("="*80)
    if dry_run:
        print(" 📡 WiFi Scanner - DRY RUN MODE (Mock Data - No Actual Scanning)")
    else:
        print(" 📡 WiFi Scanner - Active Scanning Mode (No Monitor Mode Required)")
    print("="*80)
    print()
    if dry_run:
        print(f"{YELLOW}⚠️  DRY RUN MODE: Using mock WiFi data for testing{RESET}")
        print()
    print("Configuration:")
    print(f"  Interface: {interface}")
    print(f"  Scan Method: {scan_method}")
    print(f"  Scan Interval: {scan_interval} seconds")
    print(f"  Mode: {'Continuous' if continuous else f'Timed ({duration}s)'}")
    output_config = config.get('output', {})
    if output_config.get('console', True) and output_config.get('file', False):
        print(f"  Output: Console + File ({output_config.get('file_path', '')})")
    elif output_config.get('file', False):
        print(f"  Output: File ({output_config.get('file_path', '')})")
    else:
        print("  Output: Console")
    print()
    print("What you'll see:")
    print("  • Network Name (SSID)")
    print("  • Router MAC Address (BSSID)")
    print("  • Signal Strength (RSSI in dBm)")
    print("  • Quality (Excellent/Good/Fair/Weak)")
    print()
    print("RSSI Guide:")
    print("  -30 to -50 dBm = Excellent (very close to router)")
    print("  -50 to -60 dBm = Good")
    print("  -60 to -70 dBm = Fair")
    print("  -70 to -80 dBm = Weak")
    print("  -80 to -90 dBm = Very Weak (far from router)")
    print()
    if continuous:
        if dry_run:
            print("Simulating continuous scanning... (Press Ctrl+C to stop)")
        else:
            print("Scanning continuously... (Press Ctrl+C to stop)")
    else:
        if dry_run:
            print(f"Simulating scanning for {duration} seconds... (Press Ctrl+C to stop early)")
        else:
            print(f"Scanning for {duration} seconds... (Press Ctrl+C to stop early)")
    print("="*80)
    print()

    try:
        start_time = time.time()
        scan_count = 0

        while True:
            scan_count += 1
            timestamp = datetime.now()


            if dry_run:
                networks = generate_mock_networks()
            else:
                if scan_method == 'iwlist':
                    networks = scan_wifi_iwlist(interface)
                else:
                    networks = scan_wifi_nmcli(interface)

            networks = filter_networks(networks, config)

            write_output(networks, config, scan_count, timestamp)

            if not continuous:
                if (time.time() - start_time) >= duration:
                    break

            time.sleep(scan_interval)
            
        print()
        print("="*80)
        if dry_run:
            print(f"✓ Dry run complete! ({scan_count} simulated scans performed)")
        else:
            print(f"✓ Scanning complete! ({scan_count} scans performed)")
        if config.get('output', {}).get('file', False):
            file_path = config.get('output', {}).get('file_path', 'logs/wifi_scans.csv')
            print(f"  Data saved to: {file_path}")
        if dry_run:
            print(f"  {YELLOW}Note: This was a dry run with mock data{RESET}")
        print("="*80)

    except PermissionError:
        if not dry_run:
            print()
            print(f"{RED}❌ ERROR: Permission denied!{RESET}")
            print()
            print("You need to run this script with sudo:")
            print("  sudo python3 wifi_scanner_active.py")
            print()
            print("Or use --dry-run mode to test without sudo:")
            print("  python3 wifi_scanner_active.py --dry-run")
            print()

    except KeyboardInterrupt:
        print()
        print()
        print("="*80)
        if dry_run:
            print(f"✓ Dry run stopped by user (Ctrl+C)")
        else:
            print(f"✓ Stopped by user (Ctrl+C)")
        print(f"  Total scans performed: {scan_count}")
        if config.get('output', {}).get('file', False):
            file_path = config.get('output', {}).get('file_path', 'logs/wifi_scans.csv')
            print(f"  Data saved to: {file_path}")
        if dry_run:
            print(f"  {YELLOW}Note: This was a dry run with mock data{RESET}")
        print("="*80)

    except Exception as e:
        print()
        print(f"{RED}❌ ERROR: {e}{RESET}")
        print()

if __name__ == "__main__":
    main()
