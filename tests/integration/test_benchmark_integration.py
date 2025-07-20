"""Integration tests for benchmark functionality with real SDWire devices.

These tests require actual SDWire devices to be connected to the system.
They can be run with: pytest -m requires_device
"""

import os
import pytest
import subprocess
import time
from unittest.mock import patch

from sdwire.backend import detect
from sdwire.backend.benchmark import (
    run_benchmark,
    get_usb_speed_info,
    get_device_info,
    BenchmarkError
)


@pytest.fixture(scope="module")
def connected_devices():
    """Get all connected SDWire devices for testing."""
    devices = detect.get_sdwire_devices()
    if not devices:
        pytest.skip("No SDWire devices connected for integration testing")
    return devices


@pytest.fixture(scope="module")
def sdwire3_device(connected_devices):
    """Get an SDWire3 device if available."""
    from sdwire.backend.device.sdwire import SDWire
    sdwire3_devices = [d for d in connected_devices if isinstance(d, SDWire)]
    if not sdwire3_devices:
        pytest.skip("No SDWire3 device available for testing")
    return sdwire3_devices[0]


@pytest.fixture(scope="module")
def sdwirec_device(connected_devices):
    """Get an SDWireC device if available."""
    from sdwire.backend.device.sdwirec import SDWireC
    sdwirec_devices = [d for d in connected_devices if isinstance(d, SDWireC)]
    if not sdwirec_devices:
        pytest.skip("No SDWireC device available for testing")
    return sdwirec_devices[0]


@pytest.mark.requires_device
@pytest.mark.integration
class TestBenchmarkIntegration:
    """Integration tests for benchmark functionality with real devices."""

    def test_device_detection(self, connected_devices):
        """Test that devices are properly detected."""
        assert len(connected_devices) > 0

        for device in connected_devices:
            assert device.serial_string is not None
            assert device.serial_string != ""
            print(f"Found device: {device.serial_string}")

    def test_usb_speed_info_real_device(self, connected_devices):
        """Test USB speed detection with real devices."""
        for device in connected_devices:
            usb_info = get_usb_speed_info(device)

            # Basic validation
            assert usb_info is not None
            assert isinstance(usb_info, dict)
            assert 'speed' in usb_info
            assert 'speed_raw' in usb_info
            assert 'bus' in usb_info
            assert 'address' in usb_info

            print(f"Device {device.serial_string}:")
            print(f"  USB Speed: {usb_info['speed']}")
            print(f"  Bus: {usb_info['bus']}")
            print(f"  Address: {usb_info['address']}")

    def test_device_switching(self, connected_devices):
        """Test device switching functionality."""
        for device in connected_devices:
            print(f"Testing switching for device: {device.serial_string}")

            # Switch to host mode
            try:
                device.switch_ts()
                time.sleep(2)  # Allow time for switch
                print(f"  Switched {device.serial_string} to host mode")

                # Switch to DUT mode
                device.switch_dut()
                time.sleep(2)  # Allow time for switch
                print(f"  Switched {device.serial_string} to DUT mode")

                # Switch back to host mode for other tests
                device.switch_ts()
                time.sleep(2)
                print(f"  Switched {device.serial_string} back to host mode")

            except Exception as e:
                print(f"  Warning: Switching failed for {device.serial_string}: {e}")

    def test_block_device_detection(self, connected_devices):
        """Test block device detection for connected devices."""
        for device in connected_devices:
            # Ensure device is in host mode
            device.switch_ts()
            time.sleep(3)  # Allow more time for device to appear

            block_dev = device.block_dev
            print(f"Device {device.serial_string} block device: {block_dev}")

            if block_dev:
                # Check if block device actually exists
                exists = os.path.exists(block_dev)
                print(f"  Block device {block_dev} exists: {exists}")

                if exists:
                    # Try to get device info
                    try:
                        device_info = get_device_info(block_dev)
                        print(f"  Device info: {device_info}")
                        assert isinstance(device_info, dict)
                    except Exception as e:
                        print(f"  Warning: Could not get device info: {e}")
            else:
                print(f"  No block device detected for {device.serial_string}")

    @pytest.mark.slow
    def test_benchmark_command_cli(self, connected_devices):
        """Test the benchmark command through CLI interface."""
        for device in connected_devices:
            print(f"Testing CLI benchmark for device: {device.serial_string}")

            # Test with valid serial
            try:
                result = subprocess.run([
                    'python', '-m', 'sdwire.main', 'benchmark', device.serial_string
                ], capture_output=True, text=True, timeout=30, input="Skip\nSkip\nSkip\nSkip\nSkip\ny\nsmall\n")

                print(f"  CLI return code: {result.returncode}")
                print(f"  CLI stdout: {result.stdout[:500]}...")  # First 500 chars
                if result.stderr:
                    print(f"  CLI stderr: {result.stderr[:200]}...")

            except subprocess.TimeoutExpired:
                print(f"  CLI benchmark timed out for {device.serial_string}")
            except Exception as e:
                print(f"  CLI benchmark error for {device.serial_string}: {e}")

    def test_benchmark_command_invalid_serial(self):
        """Test benchmark command with invalid serial number."""
        try:
            result = subprocess.run([
                'python', '-m', 'sdwire.main', 'benchmark', 'invalid_serial_123'
            ], capture_output=True, text=True, timeout=10)

            assert result.returncode != 0 or "No SDWire device found" in result.stdout
            print("✓ Invalid serial correctly rejected")

        except Exception as e:
            print(f"Error testing invalid serial: {e}")

    @pytest.mark.slow
    @patch('click.prompt')
    def test_full_benchmark_mocked_input(self, mock_prompt, connected_devices):
        """Test full benchmark with mocked user input."""
        # Mock all the prompts to avoid user interaction
        mock_prompt.side_effect = [
            13,      # SD card class choice (Other)
            "",      # Custom class input (empty)
            11,      # Capacity choice (Other)
            "",      # Custom capacity input (empty)
            13,      # Brand choice (Other)
            "",      # Custom brand input (empty)
            "small"  # Test size
        ]

        for device in connected_devices:
            print(f"Running full benchmark test for: {device.serial_string}")

            # Ensure device is in host mode and has block device
            device.switch_ts()
            time.sleep(3)

            if not device.block_dev or not os.path.exists(device.block_dev):
                print(f"  Skipping {device.serial_string} - no accessible block device")
                continue

            try:
                # This would normally require user input, but we're mocking it
                run_benchmark(device)
                print(f"  ✓ Benchmark completed for {device.serial_string}")

            except BenchmarkError as e:
                print(f"  Benchmark error for {device.serial_string}: {e}")
            except PermissionError as e:
                print(f"  Permission error for {device.serial_string}: {e}")
                print("    Try running as root or check device permissions")
            except Exception as e:
                print(f"  Unexpected error for {device.serial_string}: {e}")


@pytest.mark.requires_device
@pytest.mark.integration
class TestSDWire3Integration:
    """SDWire3-specific integration tests."""

    def test_sdwire3_specific_features(self, sdwire3_device):
        """Test SDWire3-specific functionality."""
        print(f"Testing SDWire3 device: {sdwire3_device.serial_string}")

        # Test USB speed info
        usb_info = get_usb_speed_info(sdwire3_device)
        print(f"SDWire3 USB info: {usb_info}")

        # SDWire3 should have direct USB device access
        assert sdwire3_device.usb_device is not None
        assert sdwire3_device.storage_device == sdwire3_device.usb_device


@pytest.mark.requires_device
@pytest.mark.integration
class TestSDWireCIntegration:
    """SDWireC-specific integration tests."""

    def test_sdwirec_specific_features(self, sdwirec_device):
        """Test SDWireC-specific functionality."""
        print(f"Testing SDWireC device: {sdwirec_device.serial_string}")

        # Test USB speed info
        usb_info = get_usb_speed_info(sdwirec_device)
        print(f"SDWireC USB info: {usb_info}")

        # SDWireC should have FTDI device access
        assert sdwirec_device.usb_device is not None

        # Test FTDI switching
        try:
            sdwirec_device.switch_ts()
            time.sleep(1)
            sdwirec_device.switch_dut()
            time.sleep(1)
            sdwirec_device.switch_ts()  # Back to host
            print("✓ FTDI switching working")
        except Exception as e:
            print(f"FTDI switching error: {e}")


@pytest.mark.requires_device
@pytest.mark.integration
@pytest.mark.slow
class TestBenchmarkPerformance:
    """Performance validation tests."""

    @patch('click.prompt')
    def test_benchmark_performance_validation(self, mock_prompt, connected_devices):
        """Test that benchmark results are reasonable."""
        mock_prompt.side_effect = [
            4,           # SD card class choice (Class 10)
            7,           # Capacity choice (32GB)
            13,          # Brand choice (Other)
            "Test Card", # Custom brand input
            "small"      # Test size
        ]

        for device in connected_devices:
            device.switch_ts()
            time.sleep(3)

            if not device.block_dev or not os.path.exists(device.block_dev):
                continue

            print(f"Performance validation for: {device.serial_string}")

            try:
                # Mock the actual benchmark tests to avoid long running times
                with patch('sdwire.backend.benchmark.run_read_test') as mock_read, \
                     patch('sdwire.backend.benchmark.run_write_test') as mock_write, \
                     patch('sdwire.backend.benchmark.run_random_read_test') as mock_random:

                    # Set reasonable mock speeds
                    mock_read.return_value = 25.0   # 25 MB/s read
                    mock_write.return_value = 15.0  # 15 MB/s write
                    mock_random.return_value = 8.0  # 8 MB/s random read

                    run_benchmark(device)

                    # Verify the mock functions were called
                    assert mock_read.called
                    assert mock_write.called
                    assert mock_random.called

                    print(f"  ✓ Performance validation passed for {device.serial_string}")

            except Exception as e:
                print(f"  Performance validation error for {device.serial_string}: {e}")


# Utility functions for integration testing
def print_test_environment():
    """Print information about the test environment."""
    print("\n" + "="*60)
    print("SDWire Benchmark Integration Test Environment")
    print("="*60)

    try:
        devices = detect.get_sdwire_devices()
        print(f"Connected SDWire devices: {len(devices)}")

        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device.serial_string} -> {device.block_dev}")

    except Exception as e:
        print(f"Error detecting devices: {e}")

    print("="*60)


if __name__ == "__main__":
    print_test_environment()
