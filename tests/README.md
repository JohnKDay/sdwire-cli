# SDWire Test Scripts

This directory contains test scripts to verify the functionality of the SDWire CLI tool with connected SDWire devices.

## Scripts Overview

### 1. `test_sdwire.sh` - Comprehensive Test Suite

A complete **automated** test suite that validates all aspects of the SDWire CLI tool functionality.

**Features:**
- ✅ Tests CLI commands (`--help`, `--version`, `list`)
- ✅ Validates device detection and listing with serial numbers
- ✅ Tests switching functionality for all connected devices
- ✅ Tests error handling (invalid serials, multiple devices without serial)
- ✅ Provides detailed pass/fail reporting with color coding
- ✅ Tests both SDWireC and SDWire3 devices
- ✅ Fully automated - no user interaction required
- ✅ Perfect for CI/automated testing environments
- ✅ Shows device serial numbers in test output

**Usage:**
```bash
./test_sdwire.sh
```

**Sample Output:**
```
[TEST 1] sdwire --version
[PASS] sdwire --version
[INFO] Testing device: 20120501030900000:3.17
[TEST 6] Switch 20120501030900000:3.17 to host
[PASS] Switch 20120501030900000:3.17 to host
```

### 2. `quick_switch_test.sh` - Quick Interactive Switch Test

A streamlined script focused on testing the core switching functionality with user verification and detailed device information.

**Features:**
- ✅ Quick device enumeration with serial numbers
- ✅ Interactive switching tests with verification prompts
- ✅ Shows device serial numbers and info in all operations
- ✅ Tests both `host` and `target` modes
- ✅ Tests alternative commands (`ts`, `dut`)
- ✅ Real-time device status display with visual formatting
- ✅ Color-coded output for better readability
- ✅ Clear indication of which device is being tested

**Usage:**
```bash
./quick_switch_test.sh
```

**Sample Output:**
```
Testing device: 20120501030900000:3.17
Device info: [0bda::0316]
[INFO] Switching device [20120501030900000:3.17] to HOST mode...
[SUCCESS] Device [20120501030900000:3.17] switched to HOST mode
```

### 3. `run_tests.sh` - Test Suite Runner

A user-friendly menu interface that helps you choose and run the appropriate test for your needs.

**Features:**
- ✅ Interactive menu system
- ✅ Prerequisites checking (command availability, device detection)
- ✅ Shows connected devices before testing
- ✅ Guides user to appropriate test choice
- ✅ Color-coded interface

**Usage:**
```bash
./run_tests.sh
```

**Menu Options:**
1. Comprehensive Test - Fully automated test suite
2. Quick Interactive Test - Manual verification test
3. Show device status only
4. Exit

## Prerequisites

1. **Connected Devices**: You should have at least one SDWire device connected (SDWireC or SDWire3)
2. **SDWire CLI**: The `sdwire` command must be available in your PATH  
3. **Permissions**: Ensure you have appropriate USB device access permissions
4. **SD Card**: For meaningful tests, an SD card should be inserted in the SDWire device
5. **Terminal**: Tests work best in a terminal that supports color output

**Quick Setup Check:**
```bash
# Check if sdwire is available
which sdwire

# Check connected devices
sdwire list

# Run the test menu
./run_tests.sh
```

## Expected Setup

The scripts are designed to work with:
- 1 SDWireC device
- 1 SDWire3 device
- Or any combination of these devices

## Test Scenarios Covered

### Device Detection
- ✅ CLI command availability
- ✅ Version information
- ✅ Help functionality
- ✅ Device listing
- ✅ Block device detection

### Switching Functionality
- ✅ Switch to host mode (`host`, `ts`)
- ✅ Switch to target mode (`target`, `dut`)
- ✅ Switch with specific serial number
- ✅ Switch without serial (single device)
- ✅ Error handling for invalid serials
- ✅ Error handling for multiple devices without serial

### Device Types
- ✅ SDWire3 devices
- ✅ SDWireC devices
- ✅ Mixed device environments

## Understanding Test Output

### Comprehensive Test (`test_sdwire.sh`)
```
[TEST 1] sdwire --version
[PASS] sdwire --version
[INFO] Testing device: 20120501030900000:3.17
[TEST 6] Switch 20120501030900000:3.17 to host
[PASS] Switch 20120501030900000:3.17 to host
[FAIL] Switch bdgrd_sdwirec_007 off (should fail)
```

### Quick Test (`quick_switch_test.sh`)
```
Testing device: bdgrd_sdwirec_007
Device info: [sd-wire::SRPOL]
[INFO] Switching device [bdgrd_sdwirec_007] to HOST mode...
[SUCCESS] Device [bdgrd_sdwirec_007] switched to HOST mode
[WAIT] Verify SD card is accessible on HOST system for device [bdgrd_sdwirec_007]
```

### Test Suite Runner (`run_tests.sh`)
```
[✓] sdwire command found
[✓] Found 2 SDWire device(s)
Connected devices:
  Serial			Product Info		Block Dev
  20120501030900000:3.17	[0bda::0316]		/dev/sdb
  bdgrd_sdwirec_007	[sd-wire::SRPOL]	/dev/sda
```

## Common Issues and Solutions

### "No SDWire devices found"
- Ensure devices are properly connected
- Check USB permissions
- Verify device recognition with `lsusb`

### "sdwire command not found"
- Install the SDWire CLI tool
- Ensure it's in your PATH
- Try running with full path to the executable

### Block device not detected
- This may be normal in some cases (device in DUT mode)
- Check if SD card is properly inserted
- Verify USB mass storage functionality

### Permission errors
- Ensure your user has access to USB devices
- Consider running with appropriate permissions
- Check udev rules if installed

## Manual Verification Points

During testing, you'll be prompted to manually verify:

1. **Host Mode**: SD card appears as a block device on the host system
   - Check with `lsblk` or file manager
   - Should be mountable and accessible

2. **Target Mode**: SD card is accessible to the target device
   - Check target device can boot from SD card
   - Or verify target device can access SD card storage

## Exit Codes

- `0`: All tests passed
- `1`: Some tests failed or error occurred
- `2`: Expected failure (used in negative test cases)

## Tips for Best Results

1. **Clean Environment**: Start with devices in a known state
2. **Proper Hardware**: Ensure SD cards are properly inserted
3. **Stable Connection**: Use reliable USB cables and ports
4. **Monitor Output**: Watch for any error messages or warnings
5. **Interactive Mode**: Pay attention to verification prompts

## Extending the Tests

To add new tests to `test_sdwire.sh`:

```bash
run_test "Test Name" "command_to_run" expected_exit_code
```

The `run_test` function handles:
- Test execution
- Exit code verification
- Pass/fail reporting
- Test counting

## Quick Start Guide

**For first-time users:**
```bash
# 1. Make scripts executable
chmod +x *.sh

# 2. Run the interactive test menu
./run_tests.sh

# 3. Choose option 2 for interactive testing
# 4. Follow prompts to verify functionality
```

**For automated testing:**
```bash
# Run comprehensive automated tests
./test_sdwire.sh

# Check exit code
echo "Test result: $?"
```

**For quick manual verification:**
```bash
# Run interactive test with manual verification
./quick_switch_test.sh
```

## Support

If tests fail consistently:
1. **Check device connections** - Ensure USB cables are secure
2. **Verify CLI installation** - Run `which sdwire` and `sdwire --version`
3. **Review error messages** - Pay attention to serial numbers and error details
4. **Test individual commands manually** - Try `sdwire list` and basic switch commands
5. **Check system logs** - Look for USB-related issues with `dmesg`
6. **Use the test menu** - Run `./run_tests.sh` for guided troubleshooting

**Device Serial Number Format:**
- **SDWire3**: `20120501030900000:3.17` (includes bus.address)
- **SDWireC**: `bdgrd_sdwirec_007` (human-readable serial)

These test scripts help ensure your SDWire setup is working correctly and can catch issues early in development or deployment scenarios. The improved scripts now show device serial numbers throughout the testing process, making it easier to identify which specific device is being tested or having issues.