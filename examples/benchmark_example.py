#!/usr/bin/env python3
"""
Example script demonstrating SDWire benchmark functionality.

This script shows how to use the SDWire benchmark module programmatically
to test SD card performance across multiple connected devices.

Note: The benchmark requires root permissions for direct device access.
You may be prompted for sudo password during execution.
"""

import sys
import time
from unittest.mock import patch
from sdwire.backend import detect
from sdwire.backend.benchmark import (
    run_benchmark,
    get_usb_speed_info,
    get_device_info,
    BenchmarkError
)


def list_available_devices():
    """List all available SDWire devices."""
    print("🔍 Detecting SDWire devices...")
    devices = detect.get_sdwire_devices()

    if not devices:
        print("❌ No SDWire devices found!")
        print("Please ensure:")
        print("  - SDWire devices are connected via USB")
        print("  - You have appropriate USB permissions")
        print("  - SD cards are inserted in the devices")
        return []

    print(f"✅ Found {len(devices)} SDWire device(s):")
    print("Serial\t\t\tType\t\tBlock Device")
    print("-" * 60)

    for device in devices:
        device_type = "SDWire3" if hasattr(device, 'generation') else "SDWireC"
        block_dev = device.block_dev or "None"
        print(f"{device.serial_string}\t{device_type}\t{block_dev}")

    return devices


def show_device_info(device):
    """Display detailed information about a specific device."""
    print(f"\n📋 Device Information: {device.serial_string}")
    print("-" * 50)

    # USB connection info
    try:
        usb_info = get_usb_speed_info(device)
        print(f"USB Speed: {usb_info['speed']}")
        print(f"USB Bus: {usb_info['bus']}")
        print(f"USB Address: {usb_info['address']}")
        print(f"VID:PID: {usb_info['vendor_id']}:{usb_info['product_id']}")
    except Exception as e:
        print(f"Could not get USB info: {e}")

    # Block device info
    if device.block_dev:
        print(f"Block Device: {device.block_dev}")
        try:
            device_info = get_device_info(device.block_dev)
            print(f"Size: {device_info.get('size', 'Unknown')}")
            print(f"Filesystem: {device_info.get('filesystem', 'Unknown')}")
            print(f"Mount Point: {device_info.get('mount_point', 'Not mounted')}")
        except Exception as e:
            print(f"Could not get device info: {e}")
    else:
        print("Block Device: Not available")


def run_quick_benchmark(device):
    """Run a quick benchmark with minimal user interaction."""
    print(f"\n⚡ Running quick benchmark for: {device.serial_string}")
    print("📋 Note: You may be prompted for sudo password for device access")

    # Mock user inputs to avoid interaction
    with patch('click.prompt') as mock_prompt, \
         patch('click.confirm') as mock_confirm:

        # Mock SD card info prompts (using numbered menu system)
        mock_prompt.side_effect = [
            4,               # SD card class choice (Class 10)
            5,               # Capacity choice (32GB)
            13,              # Brand choice (Other)
            "Test Card",     # Custom brand input
            "small"          # Test size
        ]

        # Mock sudo confirmation (automatically accept)
        mock_confirm.return_value = True

        try:
            run_benchmark(device)
            print(f"✅ Benchmark completed for {device.serial_string}")
            return True
        except BenchmarkError as e:
            if "Root permissions required" in str(e):
                print(f"❌ Sudo access declined for {device.serial_string}")
                print("   Benchmark requires root permissions for device access")
                print("   Run this script with: sudo python benchmark_example.py")
            else:
                print(f"❌ Benchmark failed for {device.serial_string}: {e}")
            return False
        except PermissionError:
            print(f"❌ Permission denied for {device.serial_string}")
            print("   Try running with sudo or check device permissions")
            print("   Example: sudo python benchmark_example.py")
            return False
        except Exception as e:
            print(f"❌ Unexpected error for {device.serial_string}: {e}")
            return False


def run_comparison_benchmark(devices):
    """Run benchmarks on multiple devices for comparison."""
    if len(devices) < 2:
        print("⚠️ Need at least 2 devices for comparison benchmark")
        return

    print(f"\n🔄 Running comparison benchmark on {len(devices)} devices...")
    results = {}

    for device in devices:
        print(f"\nTesting device: {device.serial_string}")

        # Ensure device is in host mode
        try:
            device.switch_ts()
            time.sleep(2)

            if not device.block_dev:
                print(f"  ⏭️ Skipping {device.serial_string} - no block device")
                continue

            success = run_quick_benchmark(device)
            results[device.serial_string] = success

        except Exception as e:
            print(f"  ❌ Error with {device.serial_string}: {e}")
            results[device.serial_string] = False

    # Summary
    print("\n📊 Comparison Results:")
    print("-" * 40)
    for serial, success in results.items():
        status = "✅ Passed" if success else "❌ Failed"
        print(f"{serial}: {status}")


def interactive_device_selection(devices):
    """Let user select a device interactively."""
    if len(devices) == 1:
        return devices[0]

    print("\nSelect a device to benchmark:")
    for i, device in enumerate(devices, 1):
        device_type = "SDWire3" if hasattr(device, 'generation') else "SDWireC"
        print(f"{i}. {device.serial_string} ({device_type})")

    print("\n💡 Note: Benchmarking requires sudo permissions for device access")

    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(devices)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(devices):
                return devices[index]
            else:
                print(f"Please enter a number between 1 and {len(devices)}")
        except (ValueError, KeyboardInterrupt):
            print("\nExiting...")
            return None


def main():
    """Main example function."""
    print("🎯 SDWire Benchmark Example")
    print("=" * 50)

    # Step 1: List available devices
    devices = list_available_devices()
    if not devices:
        sys.exit(1)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "info":
            # Show info for all devices
            for device in devices:
                show_device_info(device)

        elif command == "compare":
            # Run comparison benchmark
            run_comparison_benchmark(devices)

        elif command == "quick":
            # Run quick benchmark on all devices
            print("\n⚡ Running quick benchmarks on all devices...")
            for device in devices:
                run_quick_benchmark(device)

        elif command.startswith("serial:"):
            # Benchmark specific device by serial
            target_serial = command[7:]  # Remove "serial:" prefix
            target_device = None
            for device in devices:
                if device.serial_string == target_serial:
                    target_device = device
                    break

            if target_device:
                show_device_info(target_device)
                run_quick_benchmark(target_device)
            else:
                print(f"❌ Device with serial '{target_serial}' not found")

        else:
            print(f"❌ Unknown command: {command}")
            print_usage()

    else:
        # Interactive mode
        print("\n🎮 Interactive Mode")
        selected_device = interactive_device_selection(devices)
        if selected_device:
            show_device_info(selected_device)

            choice = input("\nRun benchmark? (y/N): ").strip().lower()
            if choice in ['y', 'yes']:
                run_quick_benchmark(selected_device)


def print_usage():
    """Print usage information."""
    print("\nUsage:")
    print("  python benchmark_example.py [command]")
    print("  sudo python benchmark_example.py [command]  # For actual benchmarking")
    print("\nCommands:")
    print("  info                    - Show detailed info for all devices")
    print("  quick                   - Run quick benchmark on all devices")
    print("  compare                 - Run comparison benchmark")
    print("  serial:<serial_number>  - Benchmark specific device")
    print("  (no command)            - Interactive mode")
    print("\nNote:")
    print("  Benchmarking requires root permissions for direct device access.")
    print("  You will be prompted for sudo password when needed.")
    print("\nExamples:")
    print("  python benchmark_example.py info")
    print("  sudo python benchmark_example.py quick")
    print("  sudo python benchmark_example.py compare")
    print("  sudo python benchmark_example.py serial:20120501030900000:3.17")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
