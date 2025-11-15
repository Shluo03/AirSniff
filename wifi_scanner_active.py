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
from datetime import datetime

# Color codes
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

    print("="*80)
    print(" 📡 WiFi Scanner - Active Scanning Mode (No Monitor Mode Required)")
    print("="*80)
    print()
    print("This scanner uses ACTIVE scanning (iwlist/nmcli):")
    print("  ✓ Works without monitor mode")
    print("  ✓ Works with built-in WiFi adapters")
    print("  ✗ Slower updates (1-2 seconds between scans)")
    print("  ✗ Less accurate for fast-moving platforms")
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
    print("Scanning for 30 seconds... (Press Ctrl+C to stop early)")
    print("="*80)
    print()

    # WiFi interface
    interface = "wlP1p1s0"

    # Scan method preference
    scan_method = 'iwlist'  # or 'nmcli'

    try:
        start_time = time.time()
        scan_count = 0

        while (time.time() - start_time) < 30:
            scan_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")

            print(f"\n{CYAN}[Scan #{scan_count} at {timestamp}]{RESET}")
            print("-" * 80)

            # Perform scan
            if scan_method == 'iwlist':
                networks = scan_wifi_iwlist(interface)
            else:
                networks = scan_wifi_nmcli(interface)

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
                    channel = net.get('channel', '?')

                    print(f"Network: {ssid:25s} | BSSID: {bssid:17s} | "
                          f"RSSI: {rssi:3d} dBm | Quality: {quality}")

            # Wait before next scan (avoid flooding)
            if (time.time() - start_time) < 30:
                time.sleep(1.5)  # 1.5 second delay between scans

        print()
        print("="*80)
        print(f"✓ Scanning complete! ({scan_count} scans performed)")
        print("="*80)

    except PermissionError:
        print()
        print(f"{RED}❌ ERROR: Permission denied!{RESET}")
        print()
        print("You need to run this script with sudo:")
        print("  sudo python3 wifi_scanner_active.py")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("="*80)
        print("✓ Stopped by user (Ctrl+C)")
        print("="*80)

    except Exception as e:
        print()
        print(f"{RED}❌ ERROR: {e}{RESET}")
        print()

if __name__ == "__main__":
    main()
