# Migration from pyudev to Pure pyusb Implementation

## Overview

This document outlines the migration from `pyudev` dependency to a pure `pyusb` implementation for cross-platform compatibility in the SDWire CLI tool.

## Changes Made

### 1. Removed pyudev Dependency

- **File**: `pyproject.toml`
- **Change**: Removed `pyudev = "^0.24.3"` from dependencies
- **Reason**: pyudev is Linux-specific and prevents cross-platform usage

### 2. Updated Device Detection Logic

- **File**: `sdwire/backend/detect.py`
- **Changes**:
  - Replaced `pyudev.Context().list_devices()` with `usb.core.find()`
  - Updated device attribute access to use `getattr()` for safety
  - Improved error handling for USB device access
- **Benefits**: Works on Linux, macOS, and Windows

### 3. Cross-Platform Block Device Discovery

- **File**: `sdwire/backend/block_device_utils.py` (new)
- **Features**:
  - Linux: Uses `/sys` filesystem traversal
  - macOS: Uses `system_profiler` and `diskutil`
  - Windows: Uses PowerShell WMI queries (basic implementation)
  - Fallback methods using device serial numbers

### 4. Updated Device Classes

- **Files**: 
  - `sdwire/backend/device/usb_device.py`
  - `sdwire/backend/device/sdwire.py`
  - `sdwire/backend/device/sdwirec.py`
- **Changes**:
  - Removed pyudev context initialization
  - Updated block device discovery to use new cross-platform utilities
  - Added safety checks for USB device availability

## Technical Details

### Device Detection Flow

1. **SDWire3 Detection**: Uses `usb.core.find()` with specific VID/PID filters
2. **SDWireC Detection**: Scans all USB devices and filters by product string
3. **Block Device Discovery**: Platform-specific methods to find associated storage devices

### Cross-Platform Compatibility

| Platform | Block Device Discovery Method |
|----------|-------------------------------|
| Linux    | `/sys/bus/usb/devices/` traversal |
| macOS    | `system_profiler` + `diskutil` |
| Windows  | PowerShell WMI queries |

### Error Handling

- Graceful fallback when USB string descriptors are inaccessible
- Permission error handling for system commands
- Safe attribute access using `getattr()` to prevent AttributeError

## Benefits

1. **Cross-Platform Support**: Works on Linux, macOS, and Windows
2. **Reduced Dependencies**: Eliminates Linux-specific pyudev requirement
3. **Maintained Functionality**: All existing features preserved
4. **Better Error Handling**: More robust USB device access

## Potential Limitations

1. **Windows Implementation**: Basic Windows support may need refinement for complex scenarios
2. **Permission Requirements**: Some platforms may require elevated permissions for full USB access
3. **Block Device Detection**: May not work in all virtualized environments

## Testing

The migration has been tested with:
- SDWire3 devices (VID: 0x0BDA, PID: 0x0316)
- SDWireC devices (Product: "sd-wire")
- Block device discovery on Linux systems

## Future Improvements

1. **Enhanced Windows Support**: Implement more robust Windows block device detection
2. **macOS Optimization**: Use native macOS APIs instead of command-line tools
3. **Device Monitoring**: Add support for device hotplug detection
4. **Error Recovery**: Implement automatic retry mechanisms for transient USB errors

## Migration Verification

To verify the migration was successful:

```bash
# Install dependencies (should not include pyudev)
poetry install

# Test device detection
sdwire list

# Test switching functionality
sdwire switch --serial <device_serial> ts
sdwire switch --serial <device_serial> dut
```

## Compatibility

- **Python**: Requires Python 3.12+
- **Dependencies**: pyusb, pyftdi, click (pyudev removed)
- **Platforms**: Linux, macOS, Windows (with varying levels of support)

---

**Note**: This migration maintains backward compatibility with all existing CLI commands and functionality while adding cross-platform support.