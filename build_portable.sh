#!/bin/bash
# Build script for creating a portable sdwire binary on Linux
# Tested on Ubuntu 22.04

set -e  # Exit on error

echo "======================================"
echo "Building Portable SDWire Binary"
echo "======================================"
echo ""

# Check if running on Linux
if [ "$(uname -s)" != "Linux" ]; then
    echo "Error: This script is designed for Linux systems."
    exit 1
fi

# Check for required system packages
echo "Checking for required system packages..."
REQUIRED_PACKAGES="libusb-1.0-0 python3 python3-venv"
MISSING_PACKAGES=""

for pkg in $REQUIRED_PACKAGES; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        MISSING_PACKAGES="$MISSING_PACKAGES $pkg"
    fi
done

if [ -n "$MISSING_PACKAGES" ]; then
    echo "Warning: The following packages are recommended:"
    echo "$MISSING_PACKAGES"
    echo "Install them with: sudo apt-get install$MISSING_PACKAGES"
    echo ""
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Using Python version: $PYTHON_VERSION"
echo ""

# Create / reuse a build virtualenv. Modern Debian/Ubuntu (PEP 668) blocks
# pip from installing into the system Python, so we always work inside a venv.
VENV_DIR="${VENV_DIR:-.build-venv}"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    if [ -d "$VENV_DIR" ]; then
        echo "Removing incomplete virtualenv at $VENV_DIR..."
        rm -rf "$VENV_DIR"
    fi
    echo "Creating build virtualenv at $VENV_DIR..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo ""
        echo "Error: 'python3 -m venv' failed. On Debian/Ubuntu install the venv package:"
        echo "  sudo apt-get install python3-venv"
        exit 1
    fi
else
    echo "Reusing existing build virtualenv at $VENV_DIR."
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo ""

# Upgrade pip inside the venv so wheels resolve cleanly
echo "Upgrading pip inside the virtualenv..."
pip install --upgrade pip setuptools wheel
echo ""

# Install PyInstaller and runtime dependencies
echo "Installing PyInstaller and dependencies..."
pip install pyinstaller click pyusb pyftdi
echo ""

# Install sdwire package in development mode
echo "Installing sdwire package..."
pip install -e .
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist
echo ""

# Build the portable binary
echo "Building portable binary with PyInstaller..."
pyinstaller --clean sdwire.spec
echo ""

# Check if build was successful
if [ -f "dist/sdwire" ]; then
    echo "======================================"
    echo "Build successful!"
    echo "======================================"
    echo ""
    echo "Portable binary location: dist/sdwire"
    echo ""
    echo "File size:"
    ls -lh dist/sdwire | awk '{print $5, $9}'
    echo ""
    echo "To test the binary:"
    echo "  ./dist/sdwire --help"
    echo ""
    echo "To install system-wide:"
    echo "  sudo cp dist/sdwire /usr/local/bin/"
    echo "  sudo chmod +x /usr/local/bin/sdwire"
    echo ""
    echo "Note: The binary requires libusb-1.0 to be installed on the target system:"
    echo "  sudo apt-get install libusb-1.0-0"
    echo ""
else
    echo "======================================"
    echo "Build failed!"
    echo "======================================"
    echo "Check the output above for errors."
    exit 1
fi
