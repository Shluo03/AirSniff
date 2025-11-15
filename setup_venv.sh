#!/bin/bash
# Setup virtual environment for AirSniff project
# Works on both macOS and Linux (Jetson)

set -e  # Exit on error

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "======================================"
echo " AirSniff Virtual Environment Setup"
echo "======================================"
echo ""

# Check Python version
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "✗ Python 3 not found!"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo ""
    read -p "Virtual environment already exists. Recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing old virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Detect platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ -f "/etc/nv_tegra_release" ]]; then
    PLATFORM="jetson"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
fi

echo ""
echo "Detected platform: $PLATFORM"

# Ask which requirements to install
echo ""
echo "Choose installation type:"
echo "  1) Minimal (Core WiFi monitoring - for Jetson production)"
echo "  2) Standard (Core + Visualization - recommended)"
echo "  3) Full (All dependencies including dev tools)"
read -p "Enter choice (1-3, default=2): " choice

# Default to standard if empty
choice=${choice:-2}

case $choice in
    1)
        echo ""
        echo "Installing minimal dependencies (Core WiFi monitoring)..."
        pip install scapy pandas numpy PyYAML
        ;;
    2)
        echo ""
        echo "Installing standard dependencies (Core + Visualization)..."
        pip install scapy pandas numpy PyYAML matplotlib seaborn plotly scipy psutil
        ;;
    3)
        echo ""
        echo "Installing all dependencies (Full development environment)..."
        pip install -r requirements.txt
        ;;
    *)
        echo "Invalid choice. Installing standard dependencies..."
        pip install scapy pandas numpy PyYAML matplotlib seaborn plotly scipy psutil
        ;;
esac

# Platform-specific notes
echo ""
echo "======================================"
echo " Installation Complete!"
echo "======================================"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate:"
echo "  deactivate"
echo ""

if [ "$PLATFORM" == "jetson" ]; then
    echo "⚠️  JETSON-SPECIFIC NOTES:"
    echo "  - Install system packages: sudo apt install wireless-tools iw aircrack-ng"
    echo "  - ROS 2 should be installed separately (not via pip)"
    echo "  - pycuVSLAM should be installed following NVIDIA docs"
    echo ""
elif [ "$PLATFORM" == "macos" ]; then
    echo "⚠️  macOS NOTES:"
    echo "  - Monitor mode not supported on built-in WiFi"
    echo "  - For full testing, use Jetson or external USB WiFi adapter"
    echo "  - You can still develop ROS2 nodes and test visualization"
    echo ""
fi

echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Test installation: python test_scapy_macos.py (macOS) or sudo python test_monitor_mode_jetson.py (Jetson)"
echo "  3. Read SETUP_INSTRUCTIONS.md for detailed setup"
echo ""
