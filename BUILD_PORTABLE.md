# Building Portable Binary for Linux

This document describes how to build a portable, self-contained binary for the sdwire CLI on Linux systems, specifically Ubuntu 22.04.

## Overview

The portable binary is created using PyInstaller, which bundles the Python interpreter, all Python dependencies, and the application code into a single executable file. This makes it easy to distribute and run the application without requiring users to install Python or any dependencies.

## Prerequisites

### System Requirements

- Linux system (Ubuntu 22.04 or similar)
- Python 3.10 or higher
- `libusb-1.0-0` installed on the system
- Internet connection (for downloading dependencies during build)

### Build Dependencies

Install the required system packages:

```bash
sudo apt-get update
sudo apt-get install python3 python3-pip libusb-1.0-0 libusb-1.0-0-dev
```

## Building the Portable Binary

### Automated Build (Recommended)

Use the provided build script:

```bash
./build_portable.sh
```

This script will:
1. Check for required system packages
2. Install PyInstaller and dependencies
3. Build the portable binary
4. Place the binary in `dist/sdwire`

### Manual Build

If you prefer to build manually:

1. Install PyInstaller:
   ```bash
   pip3 install --user pyinstaller
   ```

2. Install dependencies:
   ```bash
   pip3 install --user click pyusb pyftdi
   ```

3. Install sdwire in development mode:
   ```bash
   pip3 install --user -e .
   ```

4. Build the binary:
   ```bash
   python3 -m PyInstaller --clean sdwire.spec
   ```

5. The binary will be created at `dist/sdwire`

## Using the Portable Binary

### Testing

After building, test the binary:

```bash
./dist/sdwire --help
./dist/sdwire --version
```

### Installation

To install system-wide:

```bash
sudo cp dist/sdwire /usr/local/bin/
sudo chmod +x /usr/local/bin/sdwire
```

Or to a custom location:

```bash
cp dist/sdwire ~/bin/
chmod +x ~/bin/sdwire
```

### Distribution

The `dist/sdwire` binary can be distributed to other Linux systems. Users will need:

1. A Linux system (preferably Ubuntu 22.04 or similar)
2. `libusb-1.0-0` installed:
   ```bash
   sudo apt-get install libusb-1.0-0
   ```
3. Proper USB permissions (udev rules)

## USB Permissions

For non-root users to access SDWire devices, install the udev rules:

```bash
sudo cp udev/90-sdwire.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then unplug and replug the SDWire device.

## Troubleshooting

### "pyinstaller: command not found" error

If you get this error when running the build script, it means PyInstaller was installed to `~/.local/bin` which is not in your PATH. The build script has been updated to use `python3 -m PyInstaller` instead, which doesn't require PATH configuration.

If you're running an older version of the script, either:
1. Update to the latest build script, or
2. Add `~/.local/bin` to your PATH:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```
3. Or run PyInstaller directly:
   ```bash
   python3 -m PyInstaller --clean sdwire.spec
   ```

### "No backend available" error

This error indicates that libusb is not found. Install it:

```bash
sudo apt-get install libusb-1.0-0
```

### "Permission denied" when accessing USB devices

1. Install the udev rules (see above)
2. Add your user to the plugdev group:
   ```bash
   sudo usermod -a -G plugdev $USER
   ```
3. Log out and log back in

### Binary too large

The binary size is typically 15-25 MB due to bundled Python interpreter and libraries. This is normal for PyInstaller-built applications.

To reduce size, you can:
- Use UPX compression (already enabled in the spec file)
- Exclude unnecessary dependencies

### Different Python version

The binary is built with the Python version available on the build system. For maximum compatibility, build on the oldest supported Ubuntu version (22.04).

## Technical Details

### What's Bundled

The portable binary includes:
- Python 3.10+ interpreter
- click (CLI framework)
- pyusb (USB device access)
- pyftdi (FTDI device control)
- All sdwire application code

### What's NOT Bundled

The following must be present on the target system:
- libusb-1.0-0 (USB library)
- Linux kernel with USB support
- Standard Linux system libraries (glibc, etc.)

### Binary Structure

The binary is a single-file executable created with PyInstaller's "onefile" mode:
- Extracts bundled files to a temporary directory at runtime
- Runs the application
- Cleans up temporary files on exit

## Compatibility

The portable binary is compatible with:
- Ubuntu 22.04 LTS (primary target)
- Ubuntu 24.04 LTS
- Ubuntu 20.04 LTS
- Debian 11+
- Other modern Linux distributions with glibc 2.31+

## CI/CD Integration

To automate binary builds in CI/CD:

```yaml
# Example for GitHub Actions
- name: Build portable binary
  run: |
    sudo apt-get update
    sudo apt-get install -y libusb-1.0-0-dev
    ./build_portable.sh

- name: Upload binary
  uses: actions/upload-artifact@v3
  with:
    name: sdwire-linux
    path: dist/sdwire
```

## Support

For issues with building or running the portable binary, please:
1. Check that all prerequisites are installed
2. Try the troubleshooting steps above
3. Open an issue on the project repository with:
   - Your Linux distribution and version
   - Python version used for building
   - Full error output
