"""Benchmark module for SDWire devices.

This module provides functionality to benchmark read/write speeds of SD cards
connected through SDWire devices, along with USB bus speed detection and
SD card information collection.
"""

import logging
import os
import platform
import subprocess
import tempfile
import time
import getpass
import shutil
from typing import Dict, Any, Union
import click
import usb.core
from sdwire.backend.device.sdwire import SDWire
from sdwire.backend.device.sdwirec import SDWireC

log = logging.getLogger(__name__)

# Test file sizes for benchmarking (in MB)
TEST_SIZES = {
    'small': 10,   # 10MB for quick tests
    'medium': 100, # 100MB for standard tests
    'large': 500   # 500MB for thorough tests
}

# USB speed constants (since they may not be available in all pyusb versions)
SPEED_LOW = 1
SPEED_FULL = 2
SPEED_HIGH = 3
SPEED_SUPER = 4
SPEED_SUPER_PLUS = 5

# USB speed mappings
USB_SPEEDS = {
    SPEED_LOW: "1.5 Mbps (Low Speed)",
    SPEED_FULL: "12 Mbps (Full Speed)",
    SPEED_HIGH: "480 Mbps (High Speed)",
    SPEED_SUPER: "5 Gbps (SuperSpeed)",
    SPEED_SUPER_PLUS: "10 Gbps (SuperSpeed+)"
}


def check_sudo_needed(block_device: str) -> bool:
    """Check if sudo is needed to access the block device.

    Args:
        block_device: Path to block device

    Returns:
        True if sudo is needed, False otherwise
    """
    try:
        # Try to read a small amount from the device without sudo
        result = subprocess.run([
            'dd', f'if={block_device}', 'of=/dev/null', 'bs=1', 'count=1', 'status=none'
        ], capture_output=True, timeout=5)
        return result.returncode != 0
    except Exception:
        return True


def prompt_for_sudo() -> bool:
    """Prompt user about using sudo for device access.

    Returns:
        True if user agrees to use sudo, False otherwise
    """
    click.echo(click.style("\n🔐 Root permissions required for direct device access.", fg='yellow', bold=True))
    click.echo(click.style("The benchmark needs to read/write directly to the block device.", fg='white'))
    click.echo(click.style("This requires administrator privileges (sudo).", fg='white'))

    if not shutil.which('sudo'):
        click.echo(click.style("❌ sudo command not found on this system", fg='red'))
        return False

    use_sudo = click.confirm("Do you want to proceed with sudo?", default=True)

    if use_sudo:
        click.echo(click.style("💡 You may be prompted for your password...", fg='blue'))
        # Test sudo access
        try:
            result = subprocess.run(['sudo', '-n', 'true'], capture_output=True, timeout=5)
            if result.returncode != 0:
                click.echo(click.style("🔑 Please enter your password when prompted.", fg='yellow'))
        except Exception:
            pass

    return use_sudo


def run_command_with_sudo(command: list, use_sudo: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Run a command with sudo if needed.

    Args:
        command: Command list to execute
        use_sudo: Whether to use sudo
        **kwargs: Additional arguments for subprocess.run

    Returns:
        CompletedProcess result
    """
    if use_sudo:
        command = ['sudo'] + command

    return subprocess.run(command, **kwargs)


def run_benchmark(device: Union[SDWire, SDWireC]) -> None:
    """Run comprehensive benchmark on the specified SDWire device.

    Args:
        device: SDWire or SDWireC device instance to benchmark
    """
    click.echo(click.style(f"\n🔍 Starting benchmark for device: {device.serial_string}", fg='cyan', bold=True))
    click.echo(click.style("=" * 60, fg='cyan'))

    try:
        # Step 1: Get USB bus speed information
        usb_info = get_usb_speed_info(device)
        display_usb_info(usb_info)

        # Step 2: Collect SD card information from user
        sdcard_info = collect_sdcard_info()

        # Step 3: Switch device to host mode for benchmarking
        click.echo(click.style("\n📡 Switching device to HOST mode for benchmarking...", fg='blue'))
        device.switch_ts()
        time.sleep(2)  # Allow time for device to switch

        # Step 4: Verify block device is available
        block_device = device.block_dev
        if not block_device or not os.path.exists(block_device):
            raise BenchmarkError(f"Block device {block_device} not available. "
                               "Ensure SD card is inserted and device is in host mode.")

        click.echo(f"✅ Block device ready: {block_device}")

        # Step 5: Check sudo requirements
        sudo_needed = check_sudo_needed(block_device)
        use_sudo = False

        if sudo_needed:
            use_sudo = prompt_for_sudo()
            if not use_sudo:
                raise BenchmarkError("Root permissions required for device access. "
                                   "Cannot proceed without sudo privileges.")

        # Step 6: Get device and filesystem info
        device_info = get_device_info(block_device)

        # Step 7: Run benchmark tests
        results = run_benchmark_tests(block_device, use_sudo)

        # Step 8: Generate and display report
        generate_report(device, usb_info, sdcard_info, device_info, results)

    except BenchmarkError as e:
        click.echo(f"❌ Benchmark failed: {e}")
        log.error(f"Benchmark failed: {e}")
    except KeyboardInterrupt:
        click.echo("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        click.echo(f"❌ Unexpected error during benchmark: {e}")
        log.error(f"Unexpected benchmark error: {e}", exc_info=True)


def get_usb_speed_info(device: Union[SDWire, SDWireC]) -> Dict[str, Any]:
    """Get USB bus speed and connection information.

    Args:
        device: SDWire device instance

    Returns:
        Dictionary containing USB speed and connection info
    """
    usb_info = {
        'speed': 'Unknown',
        'speed_raw': None,
        'bus': 'Unknown',
        'address': 'Unknown',
        'vendor_id': 'Unknown',
        'product_id': 'Unknown'
    }

    try:
        usb_device = device.usb_device
        if usb_device:
            # Get speed information
            try:
                speed = getattr(usb_device, 'speed', None)
                if speed is not None:
                    usb_info['speed'] = USB_SPEEDS.get(speed, f"Unknown speed code: {speed}")
                    usb_info['speed_raw'] = speed
            except Exception as e:
                log.debug(f"Could not get USB speed: {e}")

            # Get bus/address info
            try:
                usb_info['bus'] = getattr(usb_device, 'bus', 'Unknown')
                usb_info['address'] = getattr(usb_device, 'address', 'Unknown')
            except Exception as e:
                log.debug(f"Could not get bus/address info: {e}")

            # Get vendor/product IDs
            try:
                usb_info['vendor_id'] = f"0x{getattr(usb_device, 'idVendor', 0):04x}"
                usb_info['product_id'] = f"0x{getattr(usb_device, 'idProduct', 0):04x}"
            except Exception as e:
                log.debug(f"Could not get vendor/product IDs: {e}")

    except Exception as e:
        log.debug(f"Error getting USB info: {e}")

    return usb_info


def display_usb_info(usb_info: Dict[str, Any]) -> None:
    """Display USB connection information.

    Args:
        usb_info: Dictionary containing USB information
    """
    click.echo(click.style("\n🔌 USB Connection Information:", fg='cyan', bold=True))
    click.echo(f"   Speed: {click.style(usb_info['speed'], fg='green')}")
    click.echo(f"   Bus: {click.style(str(usb_info['bus']), fg='green')}")
    click.echo(f"   Address: {click.style(str(usb_info['address']), fg='green')}")
    click.echo(f"   Vendor ID: {click.style(usb_info['vendor_id'], fg='green')}")
    click.echo(f"   Product ID: {click.style(usb_info['product_id'], fg='green')}")


def collect_sdcard_info() -> Dict[str, str]:
    """Collect SD card information from user through interactive numbered menus.

    Returns:
        Dictionary containing SD card information
    """
    click.echo(click.style("\n💾 SD Card Information Collection", fg='cyan', bold=True))
    click.echo(click.style("Please select your SD card specifications:", fg='white'))

    # SD card class
    click.echo(click.style("\n📊 SD Card Class:", fg='yellow', bold=True))
    class_choices = [
        'Class 2', 'Class 4', 'Class 6', 'Class 10',
        'UHS-I U1', 'UHS-I U3', 'V10', 'V30', 'V60', 'V90',
        'A1', 'A2', 'Other'
    ]

    for i, choice in enumerate(class_choices, 1):
        click.echo(f"  {click.style(str(i), fg='green')}: {choice}")

    class_idx = click.prompt(
        click.style("Select SD Card Class", fg='white'),
        type=click.IntRange(1, len(class_choices)),
        default=len(class_choices)  # Default to "Other"
    )

    if class_choices[class_idx - 1] == 'Other':
        class_info = click.prompt(
            click.style("Enter custom SD card class", fg='white'),
            default="",
            show_default=False
        )
        class_info = class_info or 'Not specified'
    else:
        class_info = class_choices[class_idx - 1]

    # Capacity
    click.echo(click.style("\n💾 Capacity:", fg='yellow', bold=True))
    capacity_choices = [
        '2GB', '4GB', '8GB', '16GB', '32GB', '64GB',
        '128GB', '256GB', '512GB', '1TB', 'Other'
    ]

    for i, choice in enumerate(capacity_choices, 1):
        click.echo(f"  {click.style(str(i), fg='green')}: {choice}")

    capacity_idx = click.prompt(
        click.style("Select Capacity", fg='white'),
        type=click.IntRange(1, len(capacity_choices)),
        default=len(capacity_choices)  # Default to "Other"
    )

    if capacity_choices[capacity_idx - 1] == 'Other':
        capacity = click.prompt(
            click.style("Enter custom capacity", fg='white'),
            default="",
            show_default=False
        )
        capacity = capacity or 'Not specified'
    else:
        capacity = capacity_choices[capacity_idx - 1]

    # Brand/Model
    click.echo(click.style("\n🏷️  Brand/Model:", fg='yellow', bold=True))
    brand_choices = [
        'SanDisk Ultra', 'SanDisk Extreme', 'SanDisk Extreme Pro',
        'Samsung EVO Select', 'Samsung EVO Plus', 'Samsung PRO Plus',
        'Kingston Canvas', 'Kingston Endurance', 'Lexar Professional',
        'Transcend Premium', 'PNY Elite', 'Sony SF-G', 'Other'
    ]

    for i, choice in enumerate(brand_choices, 1):
        click.echo(f"  {click.style(str(i), fg='green')}: {choice}")

    brand_idx = click.prompt(
        click.style("Select Brand/Model", fg='white'),
        type=click.IntRange(1, len(brand_choices)),
        default=len(brand_choices)  # Default to "Other"
    )

    if brand_choices[brand_idx - 1] == 'Other':
        brand = click.prompt(
            click.style("Enter custom brand/model", fg='white'),
            default="",
            show_default=False
        )
        brand = brand or 'Not specified'
    else:
        brand = brand_choices[brand_idx - 1]

    return {
        'class': class_info,
        'capacity': capacity,
        'brand': brand
    }


def get_device_info(block_device: str) -> Dict[str, Any]:
    """Get block device and filesystem information.

    Args:
        block_device: Path to block device (e.g., /dev/sdb)

    Returns:
        Dictionary containing device information
    """
    device_info = {
        'size': 'Unknown',
        'filesystem': 'Unknown',
        'mount_point': 'Not mounted'
    }

    system = platform.system().lower()

    try:
        if system == 'linux':
            device_info.update(_get_device_info_linux(block_device))
        elif system == 'darwin':
            device_info.update(_get_device_info_macos(block_device))
        else:
            log.warning(f"Device info not supported on platform: {system}")
    except Exception as e:
        log.debug(f"Error getting device info: {e}")

    return device_info


def _get_device_info_linux(block_device: str) -> Dict[str, Any]:
    """Get device info on Linux using lsblk and other tools."""
    info = {}

    try:
        # Get size and filesystem info using lsblk
        result = subprocess.run(
            ['lsblk', '-no', 'SIZE,FSTYPE,MOUNTPOINT', block_device],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if lines:
                parts = lines[0].split()
                if len(parts) >= 1:
                    info['size'] = parts[0]
                if len(parts) >= 2:
                    info['filesystem'] = parts[1] if parts[1] else 'Unknown'
                if len(parts) >= 3:
                    info['mount_point'] = parts[2] if parts[2] else 'Not mounted'
    except Exception as e:
        log.debug(f"Error getting Linux device info: {e}")

    return info


def _get_device_info_macos(block_device: str) -> Dict[str, Any]:
    """Get device info on macOS using diskutil."""
    info = {}

    try:
        # Extract disk identifier (e.g., disk2 from /dev/disk2)
        disk_id = os.path.basename(block_device)

        # Get disk info using diskutil
        result = subprocess.run(
            ['diskutil', 'info', disk_id],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'Total Size:' in line:
                    info['size'] = line.split(':', 1)[1].strip()
                elif 'File System Personality:' in line:
                    info['filesystem'] = line.split(':', 1)[1].strip()
                elif 'Mount Point:' in line:
                    mount_point = line.split(':', 1)[1].strip()
                    info['mount_point'] = mount_point if mount_point else 'Not mounted'
    except Exception as e:
        log.debug(f"Error getting macOS device info: {e}")

    return info


def run_benchmark_tests(block_device: str, use_sudo: bool = False) -> Dict[str, Any]:
    """Run read/write benchmark tests on the block device.

    Args:
        block_device: Path to block device
        use_sudo: Whether to use sudo for device access

    Returns:
        Dictionary containing benchmark results
    """
    click.echo("\n⚡ Running benchmark tests...")
    click.echo("This may take several minutes depending on test size.")

    results = {}

    # Ask user for test size
    test_size = click.prompt(
        "Select test size",
        type=click.Choice(['small', 'medium', 'large']),
        default='medium',
        show_choices=True
    )

    test_size_mb = TEST_SIZES[test_size]
    click.echo(click.style(f"Running {test_size} test ({test_size_mb}MB)...", fg='blue', bold=True))

    try:
        # Run sequential read test
        click.echo(click.style("\n📖 Running sequential read test...", fg='blue'))
        read_speed = run_read_test(block_device, test_size_mb, use_sudo)
        results['read_speed'] = read_speed
        click.echo(f"   Read speed: {click.style(f'{read_speed:.2f} MB/s', fg='green', bold=True)}")

        # Run sequential write test
        click.echo(click.style("\n📝 Running sequential write test...", fg='blue'))
        write_speed = run_write_test(block_device, test_size_mb, use_sudo)
        results['write_speed'] = write_speed
        click.echo(f"   Write speed: {click.style(f'{write_speed:.2f} MB/s', fg='green', bold=True)}")

        # Run random read test (smaller size)
        random_size_mb = min(test_size_mb // 4, 50)  # Smaller for random I/O
        click.echo(click.style(f"\n🎲 Running random read test ({random_size_mb}MB)...", fg='blue'))
        random_read_speed = run_random_read_test(block_device, random_size_mb, use_sudo)
        results['random_read_speed'] = random_read_speed
        click.echo(f"   Random read speed: {click.style(f'{random_read_speed:.2f} MB/s', fg='green', bold=True)}")

    except Exception as e:
        raise BenchmarkError(f"Benchmark test failed: {e}")

    return results


def run_read_test(block_device: str, size_mb: int, use_sudo: bool = False) -> float:
    """Run sequential read test using dd command.

    Args:
        block_device: Path to block device
        size_mb: Size of test in MB
        use_sudo: Whether to use sudo for device access

    Returns:
        Read speed in MB/s
    """
    try:
        # Use dd to read from device to /dev/null
        start_time = time.time()

        result = run_command_with_sudo([
            'dd',
            f'if={block_device}',
            'of=/dev/null',
            f'bs=1M',
            f'count={size_mb}',
            'iflag=direct',
            'status=none'
        ], use_sudo=use_sudo, capture_output=True, text=True, timeout=300)

        end_time = time.time()

        if result.returncode != 0:
            raise BenchmarkError(f"Read test failed: {result.stderr}")

        elapsed_time = end_time - start_time
        speed_mb_s = size_mb / elapsed_time

        return speed_mb_s

    except subprocess.TimeoutExpired:
        raise BenchmarkError("Read test timed out")
    except Exception as e:
        raise BenchmarkError(f"Read test error: {e}")


def run_write_test(block_device: str, size_mb: int, use_sudo: bool = False) -> float:
    """Run sequential write test using dd command.

    Args:
        block_device: Path to block device
        size_mb: Size of test in MB
        use_sudo: Whether to use sudo for device access

    Returns:
        Write speed in MB/s
    """
    try:
        # Create temporary file with random data
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate test data
            subprocess.run([
                'dd',
                'if=/dev/urandom',
                f'of={temp_path}',
                'bs=1M',
                f'count={size_mb}',
                'status=none'
            ], check=True, timeout=60)

            # Write test data to device
            start_time = time.time()

            result = run_command_with_sudo([
                'dd',
                f'if={temp_path}',
                f'of={block_device}',
                'bs=1M',
                'oflag=direct,sync',
                'status=none'
            ], use_sudo=use_sudo, capture_output=True, text=True, timeout=300)

            end_time = time.time()

            if result.returncode != 0:
                raise BenchmarkError(f"Write test failed: {result.stderr}")

            elapsed_time = end_time - start_time
            speed_mb_s = size_mb / elapsed_time

            return speed_mb_s

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    except subprocess.TimeoutExpired:
        raise BenchmarkError("Write test timed out")
    except Exception as e:
        raise BenchmarkError(f"Write test error: {e}")


def run_random_read_test(block_device: str, size_mb: int, use_sudo: bool = False) -> float:
    """Run random read test using dd with skip patterns.

    Args:
        block_device: Path to block device
        size_mb: Size of test in MB
        use_sudo: Whether to use sudo for device access

    Returns:
        Random read speed in MB/s
    """
    try:
        block_size = 4  # 4KB blocks for random I/O
        num_blocks = (size_mb * 1024) // block_size

        start_time = time.time()

        # Read random blocks across the device
        result = run_command_with_sudo([
            'dd',
            f'if={block_device}',
            'of=/dev/null',
            f'bs={block_size}K',
            f'count={num_blocks}',
            'iflag=direct',
            'status=none'
        ], use_sudo=use_sudo, capture_output=True, text=True, timeout=300)

        end_time = time.time()

        if result.returncode != 0:
            raise BenchmarkError(f"Random read test failed: {result.stderr}")

        elapsed_time = end_time - start_time
        speed_mb_s = size_mb / elapsed_time

        return speed_mb_s

    except subprocess.TimeoutExpired:
        raise BenchmarkError("Random read test timed out")
    except Exception as e:
        raise BenchmarkError(f"Random read test error: {e}")


def generate_report(device: Union[SDWire, SDWireC], usb_info: Dict[str, Any],
                   sdcard_info: Dict[str, str], device_info: Dict[str, Any],
                   results: Dict[str, Any]) -> None:
    """Generate and display comprehensive benchmark report.

    Args:
        device: SDWire device instance
        usb_info: USB connection information
        sdcard_info: SD card information
        device_info: Block device information
        results: Benchmark results
    """
    click.echo("\n" + "=" * 60)
    click.echo("📊 BENCHMARK REPORT")
    click.echo("=" * 60)

    # Device Information
    click.echo("\n🔧 Device Information:")
    click.echo(f"   Serial: {device.serial_string}")
    click.echo(f"   Type: {'SDWire3' if isinstance(device, SDWire) else 'SDWireC'}")
    click.echo(f"   Block Device: {device.block_dev}")

    # USB Information
    click.echo("\n🔌 USB Connection:")
    click.echo(f"   Speed: {usb_info['speed']}")
    click.echo(f"   Bus: {usb_info['bus']}")
    click.echo(f"   VID:PID: {usb_info['vendor_id']}:{usb_info['product_id']}")

    # SD Card Information
    click.echo(click.style("\n💾 SD Card Information:", fg='cyan', bold=True))
    for key, value in sdcard_info.items():
        click.echo(f"   {key.replace('_', ' ').title()}: {click.style(str(value), fg='green')}")

    # Device Details
    click.echo(click.style("\n💽 Storage Device:", fg='cyan', bold=True))
    click.echo(f"   Size: {click.style(str(device_info['size']), fg='green')}")
    click.echo(f"   Filesystem: {click.style(str(device_info['filesystem']), fg='green')}")
    click.echo(f"   Mount Point: {click.style(str(device_info['mount_point']), fg='green')}")

    # Benchmark Results
    click.echo(click.style("\n⚡ Performance Results:", fg='cyan', bold=True))
    if 'read_speed' in results:
        read_text = f"{results['read_speed']:.2f} MB/s"
        click.echo(f"   Sequential Read:  {click.style(read_text, fg='green', bold=True)}")
    if 'write_speed' in results:
        write_text = f"{results['write_speed']:.2f} MB/s"
        click.echo(f"   Sequential Write: {click.style(write_text, fg='green', bold=True)}")
    if 'random_read_speed' in results:
        random_text = f"{results['random_read_speed']:.2f} MB/s"
        click.echo(f"   Random Read:      {click.style(random_text, fg='green', bold=True)}")

    # Performance Analysis will be handled by _analyze_performance function
    _analyze_performance(usb_info, sdcard_info, results)

    click.echo("\n" + click.style("=" * 60, fg='cyan'))
    click.echo(click.style("✅ Benchmark completed successfully!", fg='green', bold=True))


def _get_sdcard_class_speeds(card_class: str) -> Dict[str, float]:
    """Get expected speeds for SD card class.

    Args:
        card_class: SD card class string

    Returns:
        Dictionary with min_write_speed and typical_read_speed in MB/s
    """
    class_speeds = {
        'class 2': {'min_write_speed': 2.0, 'typical_read_speed': 10.0},
        'class 4': {'min_write_speed': 4.0, 'typical_read_speed': 15.0},
        'class 6': {'min_write_speed': 6.0, 'typical_read_speed': 20.0},
        'class 10': {'min_write_speed': 10.0, 'typical_read_speed': 25.0},
        'uhs-i u1': {'min_write_speed': 10.0, 'typical_read_speed': 104.0},
        'uhs-i u3': {'min_write_speed': 30.0, 'typical_read_speed': 104.0},
        'v10': {'min_write_speed': 10.0, 'typical_read_speed': 90.0},
        'v30': {'min_write_speed': 30.0, 'typical_read_speed': 90.0},
        'v60': {'min_write_speed': 60.0, 'typical_read_speed': 90.0},
        'v90': {'min_write_speed': 90.0, 'typical_read_speed': 90.0},
        'a1': {'min_write_speed': 10.0, 'typical_read_speed': 25.0},
        'a2': {'min_write_speed': 10.0, 'typical_read_speed': 25.0},
    }

    class_lower = card_class.lower()
    return class_speeds.get(class_lower, {'min_write_speed': 5.0, 'typical_read_speed': 15.0})


def _analyze_performance(usb_info: Dict[str, Any], sdcard_info: Dict[str, str],
                        results: Dict[str, Any]) -> None:
    """Analyze and provide insights on benchmark performance.

    Args:
        usb_info: USB connection information
        sdcard_info: SD card information
        results: Benchmark results
    """
    read_speed = results.get('read_speed', 0)
    write_speed = results.get('write_speed', 0)

    click.echo(click.style("\n📊 Performance Analysis:", fg='cyan', bold=True))

    # SD card class analysis - primary analysis based on card specs
    card_class = sdcard_info.get('class', '')
    if card_class and card_class != 'Not specified':
        class_speeds = _get_sdcard_class_speeds(card_class)
        min_write = class_speeds['min_write_speed']
        typical_read = class_speeds['typical_read_speed']

        click.echo(click.style(f"   SD Card Class: {card_class}", fg='white'))

        # Write speed analysis against SD card spec
        if write_speed >= min_write:
            click.echo(click.style(f"   ✅ Write speed ({write_speed:.1f} MB/s) meets {card_class} specification (≥{min_write} MB/s)", fg='green'))
        elif write_speed >= min_write * 0.8:
            click.echo(click.style(f"   ⚠️  Write speed ({write_speed:.1f} MB/s) is close to {card_class} specification (≥{min_write} MB/s)", fg='yellow'))
        else:
            click.echo(click.style(f"   ❌ Write speed ({write_speed:.1f} MB/s) is below {card_class} specification (≥{min_write} MB/s)", fg='red'))

        # Read speed analysis against SD card spec
        if read_speed >= typical_read * 0.7:
            click.echo(click.style(f"   ✅ Read speed ({read_speed:.1f} MB/s) is good for {card_class} (typical ~{typical_read} MB/s)", fg='green'))
        elif read_speed >= typical_read * 0.4:
            click.echo(click.style(f"   ⚠️  Read speed ({read_speed:.1f} MB/s) is moderate for {card_class} (typical ~{typical_read} MB/s)", fg='yellow'))
        else:
            click.echo(click.style(f"   ❌ Read speed ({read_speed:.1f} MB/s) is below expected for {card_class} (typical ~{typical_read} MB/s)", fg='red'))
    else:
        click.echo(click.style("   📝 No SD card class specified - using general analysis", fg='white'))

    # Write vs Read comparison
    if read_speed > 0 and write_speed > 0:
        write_ratio = write_speed / read_speed
        if write_ratio > 0.8:
            click.echo(click.style(f"   ✅ Write/Read ratio is excellent ({write_ratio:.2f})", fg='green'))
        elif write_ratio > 0.5:
            click.echo(click.style(f"   ⚠️  Write/Read ratio is moderate ({write_ratio:.2f})", fg='yellow'))
        else:
            click.echo(click.style(f"   ❌ Write speed is significantly slower than read ({write_ratio:.2f})", fg='red'))

    # USB bottleneck analysis
    usb_speed_raw = usb_info.get('speed_raw')
    if usb_speed_raw == SPEED_HIGH:  # USB 2.0
        usb_limit = 60  # ~60 MB/s theoretical max for USB 2.0
        if read_speed > 45:
            click.echo(click.style("   ⚠️  USB 2.0 may be limiting performance (consider USB 3.0)", fg='yellow'))
    elif usb_speed_raw == SPEED_SUPER:  # USB 3.0
        usb_limit = 400  # ~400 MB/s theoretical max for USB 3.0
        if read_speed > 300:
            click.echo(click.style("   🚀 Excellent performance - utilizing USB 3.0 well", fg='green'))

    # General recommendations
    click.echo(click.style("\n💡 Recommendations:", fg='cyan', bold=True))
    if card_class and card_class != 'Not specified':
        class_speeds = _get_sdcard_class_speeds(card_class)
        if write_speed < class_speeds['min_write_speed']:
            click.echo(click.style("   • SD card may be faulty or connection issues present", fg='yellow'))

    if read_speed < 10:
        click.echo(click.style("   • Consider using a higher class SD card for better performance", fg='yellow'))
    if write_speed < 5:
        click.echo(click.style("   • Check SD card health and connection quality", fg='yellow'))

    if usb_speed_raw == SPEED_HIGH and (read_speed > 40 or write_speed > 25):
        click.echo(click.style("   • Consider upgrading to USB 3.0 for better performance", fg='yellow'))


class BenchmarkError(Exception):
    """Custom exception for benchmark-related errors."""
    pass
