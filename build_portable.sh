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
REQUIRED_PACKAGES="libusb-1.0-0 python3 python3-pip"
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

# Install PyInstaller if not already installed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
    echo ""
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install click pyusb pyftdi
echo ""

# Install sdwire package in development mode
echo "Installing sdwire package..."
pip3 install -e .
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
