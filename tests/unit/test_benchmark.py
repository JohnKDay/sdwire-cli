"""Unit tests for benchmark functionality."""

import os
import platform
import subprocess
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock, ANY
import pytest
import usb.core

from sdwire.backend.benchmark import (
    run_benchmark,
    get_usb_speed_info,
    collect_sdcard_info,
    get_device_info,
    run_benchmark_tests,
    run_read_test,
    run_write_test,
    run_random_read_test,
    generate_report,
    _analyze_performance,
    _get_device_info_linux,
    _get_device_info_macos,
    BenchmarkError,
    USB_SPEEDS,
    SPEED_HIGH,
    SPEED_SUPER,
    check_sudo_needed,
    prompt_for_sudo,
    run_command_with_sudo
)
from sdwire.backend.device.sdwire import SDWire
from sdwire.backend.device.sdwirec import SDWireC


@pytest.fixture
def mock_sdwire_device():
    """Create a mock SDWire device."""
    device = Mock(spec=SDWire)
    device.serial_string = "20120501030900000:3.17"
    device.block_dev = "/dev/sdb"
    device.usb_device = Mock()
    device.usb_device.speed = SPEED_HIGH
    device.usb_device.bus = 3
    device.usb_device.address = 17
    device.usb_device.idVendor = 0x0bda
    device.usb_device.idProduct = 0x0316
    return device


@pytest.fixture
def mock_sdwirec_device():
    """Create a mock SDWireC device."""
    device = Mock(spec=SDWireC)
    device.serial_string = "bdgrd_sdwirec_007"
    device.block_dev = "/dev/sda"
    device.usb_device = Mock()
    device.usb_device.speed = SPEED_HIGH
    device.usb_device.bus = 1
    device.usb_device.address = 5
    device.usb_device.idVendor = 0x04e8
    device.usb_device.idProduct = 0x6001
    return device


class TestGetUsbSpeedInfo:
    """Test USB speed information retrieval."""

    def test_get_usb_speed_info_success(self, mock_sdwire_device):
        """Test successful USB speed info retrieval."""
        result = get_usb_speed_info(mock_sdwire_device)

        assert result['speed'] == USB_SPEEDS[SPEED_HIGH]
        assert result['speed_raw'] == SPEED_HIGH
        assert result['bus'] == 3
        assert result['address'] == 17
        assert result['vendor_id'] == "0x0bda"
        assert result['product_id'] == "0x0316"

    def test_get_usb_speed_info_no_usb_device(self):
        """Test when USB device is not available."""
        device = Mock()
        device.usb_device = None

        result = get_usb_speed_info(device)

        assert result['speed'] == 'Unknown'
        assert result['speed_raw'] is None
        assert result['bus'] == 'Unknown'
        assert result['address'] == 'Unknown'

    def test_get_usb_speed_info_unknown_speed(self, mock_sdwire_device):
        """Test with unknown USB speed."""
        mock_sdwire_device.usb_device.speed = 999  # Unknown speed

        result = get_usb_speed_info(mock_sdwire_device)

        assert result['speed'] == "Unknown speed code: 999"
        assert result['speed_raw'] == 999

    def test_get_usb_speed_info_attribute_error(self, mock_sdwire_device):
        """Test when USB device attributes are not accessible."""
        # Remove speed attribute
        del mock_sdwire_device.usb_device.speed

        result = get_usb_speed_info(mock_sdwire_device)

        assert result['speed'] == 'Unknown'
        assert result['speed_raw'] is None


class TestCollectSdcardInfo:
    """Test SD card information collection."""

    @patch('click.prompt')
    def test_collect_sdcard_info_full_input(self, mock_prompt):
        """Test collecting complete SD card information."""
        mock_prompt.side_effect = [
            4,   # SD card class choice (Class 10)
            6,   # Capacity choice (64GB)
            1    # Brand choice (SanDisk Ultra)
        ]

        result = collect_sdcard_info()

        assert result['class'] == "Class 10"
        assert result['capacity'] == "64GB"
        assert result['brand'] == "SanDisk Ultra"

    @patch('click.prompt')
    def test_collect_sdcard_info_other_selections(self, mock_prompt):
        """Test collecting SD card info with 'Other' selections."""
        mock_prompt.side_effect = [
            13,  # SD card class choice (Other)
            "",  # Custom class input (empty)
            11,  # Capacity choice (Other)
            "",  # Custom capacity input (empty)
            13,  # Brand choice (Other)
            ""   # Custom brand input (empty)
        ]

        result = collect_sdcard_info()

        assert result['class'] == "Not specified"
        assert result['capacity'] == "Not specified"
        assert result['brand'] == "Not specified"

    @patch('click.prompt')
    def test_collect_sdcard_info_custom_inputs(self, mock_prompt):
        """Test collecting SD card info with custom inputs."""
        mock_prompt.side_effect = [
            13,               # SD card class choice (Other)
            "Custom Class",   # Custom class input
            11,               # Capacity choice (Other)
            "512MB",          # Custom capacity input
            13,               # Brand choice (Other)
            "Generic Brand"   # Custom brand input
        ]

        result = collect_sdcard_info()

        assert result['class'] == "Custom Class"
        assert result['capacity'] == "512MB"
        assert result['brand'] == "Generic Brand"

    @patch('click.prompt')
    def test_collect_sdcard_info_empty_custom_inputs(self, mock_prompt):
        """Test 'Other' selections with empty custom inputs."""
        mock_prompt.side_effect = [
            13,  # SD card class choice (Other)
            "",  # Empty custom class input
            11,  # Capacity choice (Other)
            "",  # Empty custom capacity input
            13,  # Brand choice (Other)
            ""   # Empty custom brand input
        ]

        result = collect_sdcard_info()

        assert result['class'] == "Not specified"
        assert result['capacity'] == "Not specified"
        assert result['brand'] == "Not specified"


class TestGetDeviceInfo:
    """Test device information retrieval."""

    @patch('platform.system')
    @patch('sdwire.backend.benchmark._get_device_info_linux')
    def test_get_device_info_linux(self, mock_linux_info, mock_system):
        """Test device info on Linux."""
        mock_system.return_value = "Linux"
        mock_linux_info.return_value = {
            'size': '64G',
            'filesystem': 'vfat',
            'mount_point': '/media/sdcard'
        }

        result = get_device_info("/dev/sdb")

        assert result['size'] == '64G'
        assert result['filesystem'] == 'vfat'
        assert result['mount_point'] == '/media/sdcard'
        mock_linux_info.assert_called_once_with("/dev/sdb")

    @patch('platform.system')
    @patch('sdwire.backend.benchmark._get_device_info_macos')
    def test_get_device_info_macos(self, mock_macos_info, mock_system):
        """Test device info on macOS."""
        mock_system.return_value = "Darwin"
        mock_macos_info.return_value = {
            'size': '64 GB',
            'filesystem': 'MS-DOS FAT32',
            'mount_point': '/Volumes/SDCARD'
        }

        result = get_device_info("/dev/disk2")

        assert result['size'] == '64 GB'
        assert result['filesystem'] == 'MS-DOS FAT32'
        assert result['mount_point'] == '/Volumes/SDCARD'
        mock_macos_info.assert_called_once_with("/dev/disk2")

    @patch('platform.system')
    def test_get_device_info_unsupported_platform(self, mock_system):
        """Test device info on unsupported platform."""
        mock_system.return_value = "Windows"

        result = get_device_info("/dev/sdb")

        assert result['size'] == 'Unknown'
        assert result['filesystem'] == 'Unknown'
        assert result['mount_point'] == 'Not mounted'


class TestGetDeviceInfoLinux:
    """Test Linux-specific device info retrieval."""

    @patch('subprocess.run')
    def test_get_device_info_linux_success(self, mock_run):
        """Test successful Linux device info retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="64G vfat /media/sdcard\n"
        )

        result = _get_device_info_linux("/dev/sdb")

        assert result['size'] == '64G'
        assert result['filesystem'] == 'vfat'
        assert result['mount_point'] == '/media/sdcard'

    @patch('subprocess.run')
    def test_get_device_info_linux_no_mount(self, mock_run):
        """Test Linux device info with no mount point."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="64G vfat\n"
        )

        result = _get_device_info_linux("/dev/sdb")

        assert result['size'] == '64G'
        assert result['filesystem'] == 'vfat'

    @patch('subprocess.run')
    def test_get_device_info_linux_command_failed(self, mock_run):
        """Test Linux device info when command fails."""
        mock_run.return_value = Mock(returncode=1)

        result = _get_device_info_linux("/dev/sdb")

        assert result == {}


class TestGetDeviceInfoMacos:
    """Test macOS-specific device info retrieval."""

    @patch('subprocess.run')
    def test_get_device_info_macos_success(self, mock_run):
        """Test successful macOS device info retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            Total Size: 64.0 GB (64023257088 Bytes)
            File System Personality: MS-DOS FAT32
            Mount Point: /Volumes/SDCARD
            """
        )

        result = _get_device_info_macos("/dev/disk2")

        assert result['size'] == '64.0 GB (64023257088 Bytes)'
        assert result['filesystem'] == 'MS-DOS FAT32'
        assert result['mount_point'] == '/Volumes/SDCARD'

    @patch('subprocess.run')
    def test_get_device_info_macos_command_failed(self, mock_run):
        """Test macOS device info when command fails."""
        mock_run.return_value = Mock(returncode=1)

        result = _get_device_info_macos("/dev/disk2")

        assert result == {}


class TestRunReadTest:
    """Test read speed testing."""

    @patch('sdwire.backend.benchmark.run_command_with_sudo')
    @patch('time.time')
    def test_run_read_test_success(self, mock_time, mock_run_cmd):
        """Test successful read test."""
        mock_time.side_effect = [0.0, 10.0]  # 10 second test
        mock_run_cmd.return_value = Mock(returncode=0, stderr="")

        result = run_read_test("/dev/sdb", 100, use_sudo=False)

        assert result == 10.0  # 100MB / 10s = 10 MB/s
        mock_run_cmd.assert_called_once_with([
            'dd',
            'if=/dev/sdb',
            'of=/dev/null',
            'bs=1M',
            'count=100',
            'iflag=direct',
            'status=none'
        ], use_sudo=False, capture_output=True, text=True, timeout=300)

    @patch('sdwire.backend.benchmark.run_command_with_sudo')
    def test_run_read_test_command_failed(self, mock_run_cmd):
        """Test read test when dd command fails."""
        mock_run_cmd.return_value = Mock(returncode=1, stderr="Permission denied")

        with pytest.raises(BenchmarkError) as exc_info:
            run_read_test("/dev/sdb", 100, use_sudo=False)

        assert "Read test failed: Permission denied" in str(exc_info.value)

    @patch('sdwire.backend.benchmark.run_command_with_sudo')
    def test_run_read_test_timeout(self, mock_run_cmd):
        """Test read test timeout."""
        mock_run_cmd.side_effect = subprocess.TimeoutExpired("dd", 300)

        with pytest.raises(BenchmarkError) as exc_info:
            run_read_test("/dev/sdb", 100, use_sudo=False)

        assert "Read test timed out" in str(exc_info.value)


class TestRunWriteTest:
    """Test write speed testing."""

    @patch('subprocess.run')
    @patch('sdwire.backend.benchmark.run_command_with_sudo')
    @patch('time.time')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    def test_run_write_test_success(self, mock_unlink, mock_tempfile, mock_time, mock_run_cmd, mock_run):
        """Test successful write test."""
        # Mock temporary file
        mock_temp = Mock()
        mock_temp.name = "/tmp/test_file"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        # Mock time for write test
        mock_time.side_effect = [0.0, 5.0]  # 5 second test

        # Mock subprocess calls
        mock_run.return_value = Mock(returncode=0)  # dd for data generation
        mock_run_cmd.return_value = Mock(returncode=0, stderr="")  # dd for write test

        result = run_write_test("/dev/sdb", 50, use_sudo=False)

        assert result == 10.0  # 50MB / 5s = 10 MB/s
        mock_run.assert_called_once()
        mock_run_cmd.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/test_file")

    @patch('subprocess.run')
    @patch('sdwire.backend.benchmark.run_command_with_sudo')
    @patch('tempfile.NamedTemporaryFile')
    def test_run_write_test_command_failed(self, mock_tempfile, mock_run_cmd, mock_run):
        """Test write test when dd command fails."""
        mock_temp = Mock()
        mock_temp.name = "/tmp/test_file"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        mock_run.return_value = Mock(returncode=0)  # dd for data generation
        mock_run_cmd.return_value = Mock(returncode=1, stderr="No space left on device")  # dd write fails

        with pytest.raises(BenchmarkError) as exc_info:
            run_write_test("/dev/sdb", 50, use_sudo=False)

        assert "Write test failed: No space left on device" in str(exc_info.value)


class TestRunRandomReadTest:
    """Test random read speed testing."""

    @patch('sdwire.backend.benchmark.run_command_with_sudo')
    @patch('time.time')
    def test_run_random_read_test_success(self, mock_time, mock_run_cmd):
        """Test successful random read test."""
        mock_time.side_effect = [0.0, 20.0]  # 20 second test
        mock_run_cmd.return_value = Mock(returncode=0, stderr="")

        result = run_random_read_test("/dev/sdb", 50, use_sudo=False)

        assert result == 2.5  # 50MB / 20s = 2.5 MB/s

        # Verify the command was called with correct parameters
        args = mock_run_cmd.call_args[0][0]
        assert args[0] == 'dd'
        assert args[1] == 'if=/dev/sdb'
        assert args[2] == 'of=/dev/null'
        assert args[3] == 'bs=4K'


class TestAnalyzePerformance:
    """Test performance analysis."""

    @patch('click.echo')
    def test_analyze_performance_class10_excellent(self, mock_echo):
        """Test performance analysis for excellent Class 10 performance."""
        usb_info = {'speed_raw': SPEED_HIGH}
        sdcard_info = {'class': 'Class 10'}
        results = {'read_speed': 25.0, 'write_speed': 12.0}

        _analyze_performance(usb_info, sdcard_info, results)

        # Should show SD card class analysis
        mock_echo.assert_any_call(ANY)  # Will check that colorized output is called

    @patch('click.echo')
    def test_analyze_performance_uhsi_u3_good(self, mock_echo):
        """Test performance analysis for good UHS-I U3 performance."""
        usb_info = {'speed_raw': SPEED_SUPER}
        sdcard_info = {'class': 'UHS-I U3'}
        results = {'read_speed': 80.0, 'write_speed': 35.0}

        _analyze_performance(usb_info, sdcard_info, results)

        # Should show SD card class analysis
        mock_echo.assert_any_call(ANY)  # Will check that colorized output is called

    @patch('click.echo')
    def test_analyze_performance_poor_speeds(self, mock_echo):
        """Test performance analysis for poor speeds."""
        usb_info = {'speed_raw': SPEED_HIGH}
        sdcard_info = {'class': 'Class 10'}
        results = {'read_speed': 5.0, 'write_speed': 2.0}

        _analyze_performance(usb_info, sdcard_info, results)

        # Should show SD card class analysis with poor performance indicators
        mock_echo.assert_any_call(ANY)  # Will check that colorized output is called


class TestRunBenchmarkTests:
    """Test the main benchmark test runner."""

    @patch('click.prompt')
    @patch('click.echo')
    @patch('sdwire.backend.benchmark.run_read_test')
    @patch('sdwire.backend.benchmark.run_write_test')
    @patch('sdwire.backend.benchmark.run_random_read_test')
    def test_run_benchmark_tests_success(self, mock_random_read, mock_write,
                                       mock_read, mock_echo, mock_prompt):
        """Test successful benchmark test execution."""
        mock_prompt.return_value = 'medium'
        mock_read.return_value = 50.0
        mock_write.return_value = 40.0
        mock_random_read.return_value = 25.0

        result = run_benchmark_tests("/dev/sdb")

        assert result['read_speed'] == 50.0
        assert result['write_speed'] == 40.0
        assert result['random_read_speed'] == 25.0

        mock_read.assert_called_once_with("/dev/sdb", 100, False)
        mock_write.assert_called_once_with("/dev/sdb", 100, False)
        mock_random_read.assert_called_once_with("/dev/sdb", 25, False)

    @patch('click.prompt')
    @patch('sdwire.backend.benchmark.run_read_test')
    def test_run_benchmark_tests_read_failure(self, mock_read, mock_prompt):
        """Test benchmark when read test fails."""
        mock_prompt.return_value = 'small'
        mock_read.side_effect = BenchmarkError("Read failed")

        with pytest.raises(BenchmarkError) as exc_info:
            run_benchmark_tests("/dev/sdb", use_sudo=False)

        assert "Benchmark test failed: Read failed" in str(exc_info.value)


class TestRunBenchmark:
    """Test the main benchmark function."""

    @patch('os.path.exists')
    @patch('time.sleep')
    @patch('click.echo')
    @patch('sdwire.backend.benchmark.get_usb_speed_info')
    @patch('sdwire.backend.benchmark.collect_sdcard_info')
    @patch('sdwire.backend.benchmark.get_device_info')
    @patch('sdwire.backend.benchmark.run_benchmark_tests')
    @patch('sdwire.backend.benchmark.generate_report')
    @patch('sdwire.backend.benchmark.check_sudo_needed')
    @patch('sdwire.backend.benchmark.prompt_for_sudo')
    def test_run_benchmark_success(self, mock_prompt_sudo, mock_check_sudo,
                                 mock_report, mock_tests, mock_device_info,
                                 mock_sdcard_info, mock_usb_info, mock_echo,
                                 mock_sleep, mock_exists, mock_sdwire_device):
        """Test successful benchmark execution."""
        mock_exists.return_value = True
        mock_usb_info.return_value = {
            'speed': 'USB 2.0',
            'bus': 3,
            'address': 17,
            'vendor_id': '0x0bda',
            'product_id': '0x0316'
        }
        mock_sdcard_info.return_value = {'class': 'Class 10'}
        mock_device_info.return_value = {'size': '64G'}
        mock_tests.return_value = {'read_speed': 50.0}
        mock_check_sudo.return_value = True
        mock_prompt_sudo.return_value = True

        run_benchmark(mock_sdwire_device)

        mock_sdwire_device.switch_ts.assert_called_once()
        mock_usb_info.assert_called_once_with(mock_sdwire_device)
        mock_sdcard_info.assert_called_once()
        mock_device_info.assert_called_once_with("/dev/sdb")
        mock_tests.assert_called_once_with("/dev/sdb", True)
        mock_report.assert_called_once()

    @patch('os.path.exists')
    @patch('time.sleep')
    @patch('click.echo')
    @patch('sdwire.backend.benchmark.get_usb_speed_info')
    @patch('sdwire.backend.benchmark.collect_sdcard_info')
    @patch('sdwire.backend.benchmark.check_sudo_needed')
    def test_run_benchmark_no_block_device(self, mock_check_sudo, mock_sdcard_info, mock_usb_info,
                                         mock_echo, mock_sleep, mock_exists,
                                         mock_sdwire_device):
        """Test benchmark when block device is not available."""
        mock_exists.return_value = False
        mock_usb_info.return_value = {
            'speed': 'USB 2.0',
            'bus': 3,
            'address': 17,
            'vendor_id': '0x0bda',
            'product_id': '0x0316'
        }
        mock_sdcard_info.return_value = {'class': 'Class 10'}
        mock_check_sudo.return_value = False

        run_benchmark(mock_sdwire_device)

        # Should echo error message about block device not available
        error_calls = [call for call in mock_echo.call_args_list
                      if "Block device" in str(call) and "not available" in str(call)]
        assert len(error_calls) > 0

    @patch('os.path.exists')
    @patch('time.sleep')
    @patch('click.echo')
    @patch('sdwire.backend.benchmark.get_usb_speed_info')
    @patch('sdwire.backend.benchmark.collect_sdcard_info')
    @patch('sdwire.backend.benchmark.check_sudo_needed')
    @patch('sdwire.backend.benchmark.prompt_for_sudo')
    def test_run_benchmark_sudo_declined(self, mock_prompt_sudo, mock_check_sudo,
                                       mock_sdcard_info, mock_usb_info, mock_echo,
                                       mock_sleep, mock_exists, mock_sdwire_device):
        """Test benchmark when user declines sudo access."""
        mock_exists.return_value = True
        mock_usb_info.return_value = {
            'speed': 'USB 2.0',
            'bus': 3,
            'address': 17,
            'vendor_id': '0x0bda',
            'product_id': '0x0316'
        }
        mock_sdcard_info.return_value = {'class': 'Class 10'}
        mock_check_sudo.return_value = True  # Sudo is needed
        mock_prompt_sudo.return_value = False  # User declines

        run_benchmark(mock_sdwire_device)

        # Should echo error message about permissions
        error_calls = [call for call in mock_echo.call_args_list
                      if "Root permissions required" in str(call)]
        assert len(error_calls) > 0

    @patch('click.echo')
    @patch('sdwire.backend.benchmark.get_usb_speed_info')
    def test_run_benchmark_keyboard_interrupt(self, mock_usb_info, mock_echo,
                                            mock_sdwire_device):
        """Test benchmark handling of keyboard interrupt."""
        mock_usb_info.side_effect = KeyboardInterrupt()

        run_benchmark(mock_sdwire_device)

        mock_echo.assert_any_call("\n⚠️ Benchmark interrupted by user")


class TestGenerateReport:
    """Test benchmark report generation."""

    @patch('click.echo')
    def test_generate_report_complete(self, mock_echo, mock_sdwire_device):
        """Test complete benchmark report generation."""
        usb_info = {
            'speed': '480 Mbps (High Speed)',
            'bus': 3,
            'vendor_id': '0x0bda',
            'product_id': '0x0316'
        }
        sdcard_info = {
            'class': 'Class 10',
            'capacity': '64GB',
            'brand': 'SanDisk',
            'expected_read': '100',
            'expected_write': '80'
        }
        device_info = {
            'size': '64G',
            'filesystem': 'vfat',
            'mount_point': '/media/sdcard'
        }
        results = {
            'read_speed': 50.0,
            'write_speed': 40.0,
            'random_read_speed': 25.0
        }

        generate_report(mock_sdwire_device, usb_info, sdcard_info, device_info, results)

        # Verify report sections were printed
        report_calls = [str(call) for call in mock_echo.call_args_list]
        report_text = ' '.join(report_calls)

        assert "BENCHMARK REPORT" in report_text
        assert "Device Information" in report_text
        assert "USB Connection" in report_text
        assert "SD Card Information" in report_text
        assert "Performance Results" in report_text
        assert "50.00 MB/s" in report_text  # Read speed
        assert "40.00 MB/s" in report_text  # Write speed


class TestSudoFunctionality:
    """Test sudo-related functions."""

    @patch('subprocess.run')
    def test_check_sudo_needed_true(self, mock_run):
        """Test when sudo is needed."""
        mock_run.return_value = Mock(returncode=1)  # Permission denied

        result = check_sudo_needed("/dev/sdb")

        assert result is True

    @patch('subprocess.run')
    def test_check_sudo_needed_false(self, mock_run):
        """Test when sudo is not needed."""
        mock_run.return_value = Mock(returncode=0)  # Success

        result = check_sudo_needed("/dev/sdb")

        assert result is False

    @patch('shutil.which')
    @patch('click.confirm')
    @patch('click.echo')
    def test_prompt_for_sudo_accepted(self, mock_echo, mock_confirm, mock_which):
        """Test when user accepts sudo prompt."""
        mock_which.return_value = "/usr/bin/sudo"
        mock_confirm.return_value = True

        result = prompt_for_sudo()

        assert result is True
        mock_confirm.assert_called_once_with("Do you want to proceed with sudo?", default=True)

    @patch('shutil.which')
    @patch('click.confirm')
    @patch('click.echo')
    def test_prompt_for_sudo_declined(self, mock_echo, mock_confirm, mock_which):
        """Test when user declines sudo prompt."""
        mock_which.return_value = "/usr/bin/sudo"
        mock_confirm.return_value = False

        result = prompt_for_sudo()

        assert result is False

    @patch('shutil.which')
    @patch('click.echo')
    def test_prompt_for_sudo_no_sudo_command(self, mock_echo, mock_which):
        """Test when sudo command is not available."""
        mock_which.return_value = None

        result = prompt_for_sudo()

        assert result is False

    @patch('subprocess.run')
    def test_run_command_with_sudo_true(self, mock_run):
        """Test running command with sudo."""
        mock_run.return_value = Mock(returncode=0)
        command = ['dd', 'if=/dev/sdb', 'of=/dev/null']

        result = run_command_with_sudo(command, use_sudo=True, timeout=10)

        mock_run.assert_called_once_with(['sudo'] + command, timeout=10)

    @patch('subprocess.run')
    def test_run_command_with_sudo_false(self, mock_run):
        """Test running command without sudo."""
        mock_run.return_value = Mock(returncode=0)
        command = ['dd', 'if=/dev/sdb', 'of=/dev/null']

        result = run_command_with_sudo(command, use_sudo=False, timeout=10)

        mock_run.assert_called_once_with(command, timeout=10)


class TestBenchmarkError:
    """Test BenchmarkError exception."""

    def test_benchmark_error_creation(self):
        """Test BenchmarkError can be created and raised."""
        error_msg = "Test error message"
        error = BenchmarkError(error_msg)

        assert str(error) == error_msg

        with pytest.raises(BenchmarkError) as exc_info:
            raise error

        assert str(exc_info.value) == error_msg


class TestSdcardClassSpeeds:
    """Test SD card class speed detection functionality."""

    def test_get_sdcard_class_speeds_class_10(self):
        """Test speed detection for Class 10 cards."""
        from sdwire.backend.benchmark import _get_sdcard_class_speeds

        speeds = _get_sdcard_class_speeds('Class 10')

        assert speeds['min_write_speed'] == 10
        assert speeds['typical_read_speed'] == 25

    def test_get_sdcard_class_speeds_uhs_i_u3(self):
        """Test speed detection for UHS-I U3 cards."""
        from sdwire.backend.benchmark import _get_sdcard_class_speeds

        speeds = _get_sdcard_class_speeds('UHS-I U3')

        assert speeds['min_write_speed'] == 30
        assert speeds['typical_read_speed'] == 104

    def test_get_sdcard_class_speeds_v30(self):
        """Test speed detection for V30 cards."""
        from sdwire.backend.benchmark import _get_sdcard_class_speeds

        speeds = _get_sdcard_class_speeds('V30')

        assert speeds['min_write_speed'] == 30
        assert speeds['typical_read_speed'] == 90

    def test_get_sdcard_class_speeds_case_insensitive(self):
        """Test that class detection is case insensitive."""
        from sdwire.backend.benchmark import _get_sdcard_class_speeds

        speeds_lower = _get_sdcard_class_speeds('class 10')
        speeds_upper = _get_sdcard_class_speeds('CLASS 10')
        speeds_mixed = _get_sdcard_class_speeds('Class 10')

        assert speeds_lower == speeds_upper == speeds_mixed

    def test_get_sdcard_class_speeds_unknown_class(self):
        """Test default speeds for unknown card classes."""
        from sdwire.backend.benchmark import _get_sdcard_class_speeds

        speeds = _get_sdcard_class_speeds('Unknown Class')

        assert speeds['min_write_speed'] == 5
        assert speeds['typical_read_speed'] == 15

    def test_get_sdcard_class_speeds_all_classes(self):
        """Test that all defined classes return valid speeds."""
        from sdwire.backend.benchmark import _get_sdcard_class_speeds

        test_classes = [
            'Class 2', 'Class 4', 'Class 6', 'Class 10',
            'UHS-I U1', 'UHS-I U3', 'V10', 'V30', 'V60', 'V90',
            'A1', 'A2'
        ]

        for card_class in test_classes:
            speeds = _get_sdcard_class_speeds(card_class)

            assert 'min_write_speed' in speeds
            assert 'typical_read_speed' in speeds
            assert speeds['min_write_speed'] > 0
            assert speeds['typical_read_speed'] > 0
