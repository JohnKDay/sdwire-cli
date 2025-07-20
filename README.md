# CLI for Badgerd SDWire Devices

Application also supports legacy SDWireC and non-Badger'd sdwires as well as
new Badgerd SDwire Gen2 devices.

Please see below for usage:

```
❯ sdwire --help
Usage: sdwire [OPTIONS] COMMAND [ARGS]...

Options:
--help  Show this message and exit.

Commands:
benchmark  Run benchmark tests on the specified SDWire device.
list       List all connected SDWire devices with their block device information.
switch     dut/target => connects the sdcard interface to target device

❯ sdwire switch --help
Usage: sdwire switch [OPTIONS] COMMAND [ARGS]...

  dut/target => connects the sdcard interface to target device

  ts/host => connects the sdcard interface to host machine

  off => disconnects the sdcard interface from both host and target

Options:
  -s, --serial TEXT  Serial number of the sdwire device, if there is only one
                     sdwire connected then it will be used by default
  --help             Show this message and exit.

Commands:
  dut     dut/target => connects the sdcard interface to target device
  host    ts/host => connects the sdcard interface to host machine
  off     off => disconnects the sdcard interface from both host and target
  target  dut/target => connects the sdcard interface to target device
  ts      ts/host => connects the sdcard interface to host machine
```

## Installing

Using pip

```
pip install sdwire
```

Using apt

```
sudo add-apt-repository ppa:tchavadar/badgerd
sudo apt install python3-sdwire
```

## Listing SDWire Devices

`sdwire list` command will search through usb devices connected to the system
and prints out the list of gen2 and legacy devices.

```
❯ sdwire list
Serial			Product Info
sdwire_gen2_101		[SDWire-Gen2::Badgerd Technologies]
bdgrd_sdwirec_522	[sd-wire::SRPOL]
```

## Switching SD Card Connection

`sdwire switch` command switches the sd card connection to specified direction.
If there is more than one sdwire connected to then you need specify which sdwire
you want to alter with `--serial` or `-s` options.

If there is only one sdwire connected then you dont need to specify the serial,
it will pick the one connected automatically. See the examples below.

```
❯ sdwire list
Serial			Product Info
sdwire_gen2_101		[SDWire-Gen2::Badgerd Technologies]
bdgrd_sdwirec_522	[sd-wire::SRPOL]

❯ sdwire switch -s bdgrd_sdwirec_522 target

❯ sdwire switch target
Usage: sdwire switch [OPTIONS] COMMAND [ARGS]...
Try 'sdwire switch --help' for help.

Error: There is more then 1 sdwire device connected, please use --serial|-s to specify!

❯ sdwire list
Serial			Product Info
bdgrd_sdwirec_522	[sd-wire::SRPOL]

❯ sdwire switch host
```

## Benchmarking SD Card Performance

`sdwire benchmark` command provides comprehensive performance testing for SD cards connected through SDWire devices. It measures read/write speeds, analyzes USB connection performance, and provides detailed reports with performance insights.

### Usage

```bash
sdwire benchmark <serial_number>
```

### Example

```bash
# List available devices first
❯ sdwire list
Serial                  Product Info            Block Dev
20120501030900000:3.17  [0bda::0316]           /dev/sdb
bdgrd_sdwirec_007       [sd-wire::SRPOL]       /dev/sda

# Run benchmark on a specific device
❯ sdwire benchmark 20120501030900000:3.17

🔍 Starting benchmark for device: 20120501030900000:3.17
============================================================

🔌 USB Connection Information:
   Speed: 480 Mbps (High Speed)
   Bus: 3
   Address: 17
   Vendor ID: 0x0bda
   Product ID: 0x0316

💾 SD Card Information Collection
Please select your SD card specifications:

📊 SD Card Class:
  1: Class 2
  2: Class 4
  3: Class 6
  4: Class 10
  5: UHS-I U1
  6: UHS-I U3
  7: V10
  8: V30
  9: V60
  10: V90
  11: A1
  12: A2
  13: Other
Select SD Card Class [13]: 4

💾 Capacity:
  1: 2GB
  2: 4GB
  3: 8GB
  4: 16GB
  5: 32GB
  6: 64GB
  7: 128GB
  8: 256GB
  9: 512GB
  10: 1TB
  11: Other
Select Capacity [11]: 6

🏷️  Brand/Model:
  1: SanDisk Ultra
  2: SanDisk Extreme
  3: SanDisk Extreme Pro
  4: Samsung EVO Select
  5: Samsung EVO Plus
  6: Samsung PRO Plus
  7: Kingston Canvas
  8: Kingston Endurance
  9: Lexar Professional
  10: Transcend Premium
  11: PNY Elite
  12: Sony SF-G
  13: Other
Select Brand/Model [13]: 1

📡 Switching device to HOST mode for benchmarking...
✅ Block device ready: /dev/sdb

🔐 Root permissions required for direct device access.
The benchmark needs to read/write directly to the block device.
This requires administrator privileges (sudo).
Do you want to proceed with sudo? [Y/n]: y
💡 You may be prompted for your password...

⚡ Running benchmark tests...
Select test size (small/medium/large) [medium]: small

📖 Running sequential read test...
   Read speed: 45.30 MB/s

📝 Running sequential write test...
   Write speed: 23.50 MB/s

🎲 Running random read test (2MB)...
   Random read speed: 12.80 MB/s

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

⚡ Performance Results:
   Sequential Read:  45.30 MB/s
   Sequential Write: 23.50 MB/s
   Random Read:      12.80 MB/s

📊 Performance Analysis:
   SD Card Class: Class 10
   ✅ Write speed (23.50 MB/s) meets Class 10 specification (≥10 MB/s)
   ✅ Read speed (45.30 MB/s) is good for Class 10 (typical ~25 MB/s)
   ⚠️  Write/Read ratio is moderate (0.52)

💡 Recommendations:
   • Consider upgrading to USB 3.0 for better performance

✅ Benchmark completed successfully!
```

### Test Sizes

- **Small (10MB)**: Quick test, takes 30-60 seconds
- **Medium (100MB)**: Standard test, takes 2-5 minutes  
- **Large (500MB)**: Thorough test, takes 5-15 minutes

### Requirements

- **Sudo access**: Required for direct block device access (automatically prompted)
- **SD card**: Must be inserted in the SDWire device
- **Interactive terminal**: For password prompts and user input
- Device will be automatically switched to host mode during testing

### Cross-Platform Support

The benchmark command works on both Linux and macOS:
- **Linux**: Uses `lsblk` and `dd` commands with automatic sudo handling
- **macOS**: Uses `diskutil` and `dd` commands with automatic sudo handling
- **Permission Management**: Automatically detects and prompts for sudo when needed

For detailed documentation, see [docs/BENCHMARK.md](docs/BENCHMARK.md).
