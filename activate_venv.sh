#!/bin/bash
# Quick activation script for AirSniff virtual environment
# Usage: source activate_venv.sh  (or . activate_venv.sh)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "✗ Virtual environment not found!"
    echo "  Run: ./setup_venv.sh"
    return 1
fi

source "$VENV_DIR/bin/activate"
echo "✓ AirSniff virtual environment activated"
echo "  Python: $(which python3)"
echo "  To deactivate: deactivate"
