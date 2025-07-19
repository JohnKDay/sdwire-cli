# SDWire Benchmark Command

The `sdwire benchmark` command provides comprehensive performance testing for SD cards connected through SDWire devices. It measures read/write speeds, analyzes USB connection performance, and provides detailed reports with performance insights.

## Table of Contents

- [Overview](#overview)
- [Usage](#usage)
- [Prerequisites](#prerequisites)
- [Test Procedure](#test-procedure)
- [Understanding the Output](#understanding-the-output)
- [Performance Analysis](#performance-analysis)
- [Test Sizes](#test-sizes)
- [Cross-Platform Support](#cross-platform-support)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

The benchmark command performs the following operations:

1. **USB Connection Analysis**: Detects USB bus speed and connection details
2. **SD Card Information Collection**: Gathers user-provided SD card specifications
3. **Device Switching**: Automatically switches the SDWire to host mode for testing
4. **Performance Testing**: Runs sequential read, write, and random read tests
5. **Report Generation**: Provides detailed analysis and performance insights

## Usage

```bash
sdwire benchmark <serial_number>
```

### Parameters

- `serial_number`: The serial number of the SDWire device to benchmark
  - Use `sdwire list` to see available devices and their serial numbers

### Example

```bash
# List available devices
sdwire list
Serial                  Product Info            Block Dev
20120501030900000:3.17  [0bda::0316]           /dev/sdb
bdgrd_sdwirec_007       [sd-wire::SRPOL]       /dev/sda

# Run benchmark on SDWire3 device
sdwire benchmark 20120501030900000:3.17

# Run benchmark on SDWireC device
sdwire benchmark bdgrd_sdwirec_007
```

## Prerequisites

### System Requirements

- **Linux**: Ubuntu 18.04+ or equivalent
- **macOS**: macOS 10.14+ (Mojave or later)
- **Python**: 3.12 or later
- **Permissions**: Root/administrator access may be required for device access

### Hardware Requirements

- Connected SDWire device (SDWire3 or SDWireC)
- SD card inserted in the SDWire device
- Stable USB connection

### Permission Requirements

- **Root/administrator access**: Required for direct block device access
- **sudo command**: Must be available on the system
- **Interactive sudo**: You will be prompted for password during benchmark

### Dependencies

The benchmark command requires these packages (automatically installed):
- `click` - Command line interface
- `pyusb` - USB device access
- `pyftdi` - FTDI device control (for SDWireC)

## Test Procedure

### 1. USB Connection Analysis

The benchmark automatically detects:
- USB bus speed (USB 2.0, USB 3.0, etc.)
- Bus number and device address
- Vendor and Product IDs

### 2. SD Card Information Collection

You'll be prompted with choice-based menus for SD card details:

```
💾 SD Card Information Collection:
Please select your SD card specifications:
SD Card Class (Class 2, Class 4, Class 6, Class 10, UHS-I U1, UHS-I U3, V10, V30, V60, V90, A1, A2, Other, Skip) [Other]: Class 10
Capacity (2GB, 4GB, 8GB, 16GB, 32GB, 64GB, 128GB, 256GB, 512GB, 1TB, Other, Skip) [Other]: 64GB
Brand/Model (SanDisk Ultra, SanDisk Extreme, SanDisk Extreme Pro, Samsung EVO Select, Samsung EVO Plus, Samsung PRO Plus, Kingston Canvas, Kingston Endurance, Lexar Professional, Transcend Premium, PNY Elite, Sony SF-G, Other, Skip) [Other]: SanDisk Ultra
Expected Read Speed (10 MB/s, 25 MB/s, 50 MB/s, 80 MB/s, 100 MB/s, 150 MB/s, 200 MB/s, Other, Skip) [Skip]: 100 MB/s
Expected Write Speed (5 MB/s, 10 MB/s, 20 MB/s, 30 MB/s, 50 MB/s, 80 MB/s, 100 MB/s, Other, Skip) [Skip]: 80 MB/s
```

**Features**:
- **Predefined choices** for common SD card specifications
- **"Other" option** allows custom input for unlisted values
- **"Skip" option** to omit any field
- **Default "Other"** for most fields, "Skip" for speeds

### 3. Device Switching

The device is automatically switched to host mode for testing. You'll see:

```
📡 Switching device to HOST mode for benchmarking...
✅ Block device ready: /dev/sdb
```

### 4. Permission Check and Sudo Prompt

The benchmark automatically checks if root permissions are needed and prompts:

```
🔐 Root permissions required for direct device access.
The benchmark needs to read/write directly to the block device.
This requires administrator privileges (sudo).
Do you want to proceed with sudo? [Y/n]: y
💡 You may be prompted for your password...
```

### 5. Performance Testing

You'll be asked to select a test size:

```
Select test size (small/medium/large) [medium]: medium
```

The benchmark runs three types of tests:
- **Sequential Read**: Large block sequential reading
- **Sequential Write**: Large block sequential writing  
- **Random Read**: Small block random access reading

## Understanding the Output

### Sample Report

```
============================================================
📊 BENCHMARK REPORT
============================================================

🔧 Device Information:
   Serial: 20120501030900000:3.17
   Type: SDWire3
   Block Device: /dev/sdb

🔌 USB Connection:
   Speed: 480 Mbps (High Speed)
   Bus: 3
   VID:PID: 0x0bda:0x0316

💾 SD Card Information:
   Class: Class 10
   Capacity: 64GB
   Brand: SanDisk Ultra
   Expected Read: 100 MB/s
   Expected Write: 80 MB/s

💽 Storage Device:
   Size: 64G
   Filesystem: vfat
   Mount Point: Not mounted

⚡ Performance Results:
   Sequential Read:  45.30 MB/s
   Sequential Write: 23.50 MB/s
   Random Read:      12.80 MB/s

📈 Performance Analysis:
   ✅ Read speed is excellent for USB 2.0
   ⚠️ Write speed is moderately slower than read speed
   ✅ Write speed meets SD card class specification
   💡 Consider using a higher class SD card for better performance
```

### Result Interpretation

#### USB Speed Analysis
- **USB 2.0 (480 Mbps)**: Theoretical max ~60 MB/s
- **USB 3.0 (5 Gbps)**: Theoretical max ~400 MB/s
- Performance is rated as excellent (>80%), good (>50%), or poor (<50%)

#### Read vs Write Performance
- **Write Ratio > 80%**: Excellent write performance
- **Write Ratio > 50%**: Good write performance  
- **Write Ratio < 50%**: Poor write performance (may indicate SD card limitations)

#### SD Card Class Validation
- **Class 10**: Minimum 10 MB/s write speed
- **UHS-I U1**: Minimum 10 MB/s write speed
- **UHS-I U3**: Minimum 30 MB/s write speed
- **V30**: Minimum 30 MB/s video write speed

## Performance Analysis

### Status Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Excellent performance |
| ⚠️ | Good but could be better |
| ❌ | Below expected performance |
| 💡 | Recommendation or tip |

### Common Performance Patterns

#### Excellent Performance
```
✅ Read speed is excellent for USB 2.0
✅ Write speed is very close to read speed
✅ Write speed meets SD card class specification
```

#### Moderate Performance
```
⚠️ Read speed is good but could be better
⚠️ Write speed is moderately slower than read speed
```

#### Poor Performance
```
❌ Read speed is below expected for USB 2.0
❌ Write speed is significantly slower than read speed
⚠️ Write speed below SD card class specification
```

## Test Sizes

| Size | Data Amount | Use Case | Duration |
|------|-------------|----------|----------|
| Small | 10 MB | Quick test | 30-60 seconds |
| Medium | 100 MB | Standard test | 2-5 minutes |
| Large | 500 MB | Thorough test | 5-15 minutes |

**Recommendations**:
- Use **small** for quick validation
- Use **medium** for regular testing
- Use **large** for comprehensive analysis

## Cross-Platform Support

### Linux
- Uses `lsblk` for device information
- Uses `dd` for performance testing
- Requires appropriate device permissions

### macOS
- Uses `system_profiler` and `diskutil` for device information
- Uses `dd` for performance testing
- May require administrative privileges

### Automatic Permission Handling

The benchmark command automatically handles permission requirements:

1. **Permission Check**: Automatically detects if sudo is needed
2. **User Prompt**: Asks for permission to use sudo if required
3. **Graceful Handling**: Provides clear error messages if declined

#### Typical Flow
```bash
# Run benchmark normally - no need to prefix with sudo
sdwire benchmark <serial>

# The command will automatically prompt for sudo if needed:
# 🔐 Root permissions required for direct device access.
# Do you want to proceed with sudo? [Y/n]: y
# [sudo] password for user: [enter password]
```

#### Manual sudo (if preferred)
```bash
# You can still run with sudo manually
sudo sdwire benchmark <serial>
```

## Troubleshooting

### Common Issues

#### "No SDWire device found with serial"
```bash
# Solution: Check connected devices
sdwire list

# Ensure the serial number is correct
sdwire benchmark "exact_serial_from_list"
```

#### "Block device not available"
```bash
# Solution: Ensure SD card is inserted and device is in host mode
sdwire switch -s <serial> host
# Wait a few seconds, then try benchmark again
```

#### "Permission denied"
```bash
# The benchmark should automatically prompt for sudo.
# If you see permission denied:

# 1. Accept the sudo prompt when asked
# 2. Ensure sudo is available: which sudo
# 3. Check if you have sudo privileges: sudo -v

# Manual approach (if automatic sudo fails):
sudo sdwire benchmark <serial>
```

#### "Read test failed"
```bash
# Possible causes:
# 1. SD card not properly inserted
# 2. Device not in host mode
# 3. File system errors on SD card

# Solutions:
# 1. Re-insert SD card
# 2. Manual switch: sdwire switch -s <serial> host
# 3. Check SD card with disk utility
```

#### "Write test failed"
```bash
# Possible causes:
# 1. SD card is write-protected
# 2. SD card is full
# 3. File system is read-only

# Solutions:
# 1. Check write-protect switch on SD card
# 2. Use a different SD card with free space
# 3. Reformat SD card if needed
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
sdwire --debug benchmark <serial>
```

## Examples

### Basic Benchmark
```bash
$ sdwire benchmark 20120501030900000:3.17

🔍 Starting benchmark for device: 20120501030900000:3.17
============================================================

🔌 USB Connection Information:
   Speed: 480 Mbps (High Speed)
   Bus: 3
   Address: 17
   Vendor ID: 0x0bda
   Product ID: 0x0316

💾 SD Card Information Collection:
Please select your SD card specifications:
SD Card Class (Class 2, Class 4, Class 6, Class 10, UHS-I U1, UHS-I U3, V10, V30, V60, V90, A1, A2, Other, Skip) [Other]: Class 10
Capacity (2GB, 4GB, 8GB, 16GB, 32GB, 64GB, 128GB, 256GB, 512GB, 1TB, Other, Skip) [Other]: 32GB
Brand/Model (SanDisk Ultra, SanDisk Extreme, SanDisk Extreme Pro, Samsung EVO Select, Samsung EVO Plus, Samsung PRO Plus, Kingston Canvas, Kingston Endurance, Lexar Professional, Transcend Premium, PNY Elite, Sony SF-G, Other, Skip) [Other]: Skip
Expected Read Speed (10 MB/s, 25 MB/s, 50 MB/s, 80 MB/s, 100 MB/s, 150 MB/s, 200 MB/s, Other, Skip) [Skip]: Skip
Expected Write Speed (5 MB/s, 10 MB/s, 20 MB/s, 30 MB/s, 50 MB/s, 80 MB/s, 100 MB/s, Other, Skip) [Skip]: Skip

📡 Switching device to HOST mode for benchmarking...
✅ Block device ready: /dev/sdb

🔐 Root permissions required for direct device access.
The benchmark needs to read/write directly to the block device.
This requires administrator privileges (sudo).
Do you want to proceed with sudo? [Y/n]: y
💡 You may be prompted for your password...
[sudo] password for user: ********

⚡ Running benchmark tests...
This may take several minutes depending on test size.
Select test size (small/medium/large) [medium]: small

📖 Running sequential read test...
   Read speed: 43.25 MB/s

📝 Running sequential write test...
   Write speed: 18.90 MB/s

🎲 Running random read test (2MB)...
   Random read speed: 15.60 MB/s

============================================================
📊 BENCHMARK REPORT
============================================================
[... full report ...]
```

### High-Performance SD Card Example
```bash
# Testing a UHS-I U3 card
SD Card Class: UHS-I U3
Capacity: 128GB
Brand/Model: SanDisk Extreme Pro
Expected Read Speed (MB/s): 170
Expected Write Speed (MB/s): 90

# Expected results:
Sequential Read:  ~50-60 MB/s (USB 2.0 limited)
Sequential Write: ~30-40 MB/s (good for U3 class)
Random Read:      ~20-30 MB/s
```

### USB 3.0 vs USB 2.0 Comparison
```bash
# USB 2.0 Connection (typical results)
Sequential Read:  45 MB/s
Sequential Write: 25 MB/s

# USB 3.0 Connection (same SD card)
Sequential Read:  85 MB/s
Sequential Write: 60 MB/s
```

## Best Practices

### Before Testing
1. **Use a fresh SD card** or reformat if needed
2. **Ensure stable USB connection** - avoid USB hubs if possible
3. **Close other applications** that might use the device
4. **Check SD card specifications** for comparison

### During Testing
1. **Don't interrupt the test** - let it complete fully
2. **Monitor system resources** - ensure adequate free memory
3. **Note any error messages** for troubleshooting

### After Testing
1. **Save results** for comparison over time
2. **Compare with SD card specifications** to validate hardware
3. **Document any performance issues** for further investigation

### Performance Optimization Tips
1. **Use USB 3.0 ports** when available for better throughput
2. **Use high-quality SD cards** (Class 10, U3, V30) for better performance
3. **Avoid daisy-chained USB hubs** which can reduce performance
4. **Ensure adequate power supply** to USB ports

## Integration with CI/CD

The benchmark command can be integrated into automated testing:

```bash
#!/bin/bash
# Automated benchmark script

# Run benchmark with predefined inputs (including sudo confirmation)
echo -e "Skip\nSkip\nSkip\nSkip\nSkip\ny\nsmall" | sdwire benchmark $DEVICE_SERIAL

# Check exit code
if [ $? -eq 0 ]; then
    echo "Benchmark passed"
    exit 0
else
    echo "Benchmark failed"
    exit 1
fi

# Alternative: Run with sudo upfront to avoid prompts
# sudo sdwire benchmark $DEVICE_SERIAL < input.txt
```

## Contributing

If you encounter issues or have suggestions for improving the benchmark functionality:

1. Check existing issues in the project repository
2. Provide detailed error messages and system information
3. Include the full benchmark output when reporting problems
4. Test with multiple SD cards when possible to isolate issues

For more information, see the main [README.md](../README.md) and [MIGRATION_NOTES.md](../MIGRATION_NOTES.md).