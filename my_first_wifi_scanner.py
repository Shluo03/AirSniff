#!/usr/bin/env python3
"""
My First WiFi Scanner
=====================
This script scans for WiFi networks and displays their signal strength (RSSI).

"""

# Import scapy for WiFi packet capture
# type: ignore comments tell the IDE to ignore false warnings
try:
    from scapy.all import sniff, Dot11Beacon, RadioTap  # type: ignore
except ImportError:
    print("ERROR: Scapy not installed!")
    print("Install with: pip install scapy")
    print("Or activate venv: source venv/bin/activate")
    exit(1)

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
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

def packet_handler(packet):
    """
    This function is called for EVERY WiFi packet we capture.

    We only care about beacon frames (routers announcing themselves).
    """

    if packet.haslayer(Dot11Beacon):

        try:
            ssid = packet.info.decode('utf-8', errors='ignore')
            if not ssid:  # Hidden network
                ssid = "<Hidden Network>"
        except:
            ssid = "<Unknown>"

        bssid = packet.addr2

        # Extract the signal strength (RSSI)
        try:

            if packet.haslayer(RadioTap):
                rssi = packet.dBm_AntSignal
                quality = get_signal_quality(rssi)

                print(f"Network: {ssid:25s} | BSSID: {bssid} | RSSI: {rssi:3d} dBm | Quality: {quality}")
            else:
                print(f"Network: {ssid:25s} | BSSID: {bssid} | RSSI: N/A")

        except AttributeError:
            print(f"Network: {ssid:25s} | BSSID: {bssid} | RSSI: N/A")

def main():
    """
    Main function - starts the WiFi scanner.
    """

    print("="*80)
    print(" 📡 WiFi Scanner - Detecting Networks and Signal Strength (RSSI)")
    print("="*80)
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

    interface = "wlan0"

    try:

        sniff(
            iface=interface,
            prn=packet_handler,
            timeout=30,
            store=False
        )

        print()
        print("="*80)
        print("✓ Scanning complete!")
        print("="*80)

    except PermissionError:
        print()
        print("❌ ERROR: Permission denied!")
        print()
        print("You need to run this script with sudo:")
        print("  sudo python3 my_first_wifi_scanner.py")
        print()

    except OSError as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        print("Common issues:")
        print("  1. Interface 'wlan0' doesn't exist")
        print("     → Check your interface: iwconfig")
        print("     → Update 'interface' variable in this script")
        print()
        print("  2. Interface not in monitor mode")
        print("     → Run: sudo ip link set wlan0 down")
        print("     → Run: sudo iw dev wlan0 set monitor none")
        print("     → Run: sudo ip link set wlan0 up")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("="*80)
        print("✓ Stopped by user (Ctrl+C)")
        print("="*80)

if __name__ == "__main__":
    main()
