import os
import platform
import logging
import subprocess
import re
import signal
from typing import Optional
import usb.core

log = logging.getLogger(__name__)


def find_block_device_for_usb(usb_device: usb.core.Device) -> Optional[str]:
    """
    Find the block device path for a given USB device.

    Args:
        usb_device: USB device object from pyusb

    Returns:
        Block device path (e.g., '/dev/sda', '/dev/disk2', '\\\\.\\PhysicalDrive0')
        or None if not found
    """
    system = platform.system().lower()

    if system == 'linux':
        return _find_block_device_linux(usb_device)
    elif system == 'darwin':  # macOS
        return _find_block_device_macos(usb_device)
    elif system == 'windows':
        return _find_block_device_windows(usb_device)
    else:
        log.warning(f"Unsupported platform: {system}")
        return None


def _find_usb_device_path(bus: int, address: int) -> Optional[str]:
    """Find the actual USB device path in /sys/bus/usb/devices/ based on bus and address."""
    try:
        # Add timeout protection for directory operations
        def timeout_handler(signum, frame):
            raise TimeoutError("USB device path search timed out")

        # Set a 2 second timeout for this operation
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)

        try:
            if not os.path.exists("/sys/bus/usb/devices/"):
                return None

            for device_dir in os.listdir("/sys/bus/usb/devices/"):
                device_path = f"/sys/bus/usb/devices/{device_dir}"
                if not os.path.isdir(device_path):
                    continue

                try:
                    # Check if this directory has busnum and devnum files
                    busnum_file = os.path.join(device_path, "busnum")
                    devnum_file = os.path.join(device_path, "devnum")

                    if os.path.exists(busnum_file) and os.path.exists(devnum_file):
                        with open(busnum_file, "r") as f:
                            device_bus = int(f.read().strip())
                        with open(devnum_file, "r") as f:
                            device_address = int(f.read().strip())

                        if device_bus == bus and device_address == address:
                            return device_path
                except (OSError, ValueError, IOError):
                    continue
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    except (TimeoutError, OSError, IOError) as e:
        log.debug(f"Error searching for USB device path: {e}")

    return None


def _find_block_device_linux(usb_device: usb.core.Device) -> Optional[str]:
    """Find block device on Linux using /sys filesystem."""
    try:
        # Get USB device info
        bus = getattr(usb_device, 'bus', None)
        address = getattr(usb_device, 'address', None)
        vendor_id = getattr(usb_device, 'idVendor', 0)
        product_id = getattr(usb_device, 'idProduct', 0)

        # Ensure we have valid bus and address
        if bus is None or address is None:
            log.debug("USB device missing bus or address information")
            return None

        # Find the actual USB device path using bus and address
        usb_device_path = _find_usb_device_path(bus, address)

        if not usb_device_path:
            log.debug(f"USB device path not found for bus {bus}, address {address}")
            return None

        log.debug(f"Found USB device path: {usb_device_path}")

        # Debug VID/PID detection
        log.debug(f"Device VID: {vendor_id:04x}, PID: {product_id:04x}")
        log.debug(f"Expected SDWireC VID: {0x04e8:04x}, PID: {0x6001:04x}")
        log.debug(f"VID match: {vendor_id == 0x04e8}, PID match: {product_id == 0x6001}")

        # Handle different device topologies
        if vendor_id == 0x04e8 and product_id == 0x6001:
            # SDWireC: FTDI chip, need to find sibling mass storage device
            log.debug("Taking SDWireC sibling detection path")
            log.debug(f"About to call _find_sdwirec_block_device with path: {usb_device_path}")
            result = _find_sdwirec_block_device(usb_device_path)
            log.debug(f"SDWireC function returned: {result}")
            return result
        else:
            # SDWire3 or other: Direct mass storage device
            log.debug("Taking SDWire3/other direct detection path")
            return _search_block_devices_recursive(usb_device_path)

    except Exception as e:
        log.debug(f"Error finding block device on Linux: {e}")
        return None


def _find_sdwirec_block_device(ftdi_device_path: str) -> Optional[str]:
    """Find block device for SDWireC by looking for sibling mass storage device."""
    try:
        # Add timeout protection for SDWireC sibling detection
        def timeout_handler(signum, frame):
            raise TimeoutError("SDWireC sibling detection timed out")

        # Set a 3 second timeout for this operation
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3)

        try:
            log.debug(f"SDWireC: Starting sibling detection for path: {ftdi_device_path}")

            # Check if FTDI device path still exists
            if not os.path.exists(ftdi_device_path):
                log.debug(f"SDWireC: FTDI device path no longer exists: {ftdi_device_path}")
                return None

            # Extract the device name from path (e.g., "3-1.2" from "/sys/bus/usb/devices/3-1.2")
            device_name = os.path.basename(ftdi_device_path)
            log.debug(f"SDWireC: FTDI device name: {device_name}")
            log.debug(f"SDWireC: FTDI device full path: {ftdi_device_path}")

            # Extract hub pattern (e.g., "3-1" from "3-1.2")
            if '.' in device_name:
                hub_pattern = device_name.rsplit('.', 1)[0]
                log.debug(f"SDWireC: Looking for siblings of hub pattern: {hub_pattern}")

                # Look for sibling devices with same hub pattern
                usb_devices_dir = "/sys/bus/usb/devices"
                if not os.path.exists(usb_devices_dir):
                    log.debug(f"SDWireC: USB devices directory not found: {usb_devices_dir}")
                    return None

                log.debug(f"SDWireC: Scanning {usb_devices_dir} for siblings")
                try:
                    entries = os.listdir(usb_devices_dir)
                except (OSError, IOError) as e:
                    log.debug(f"SDWireC: Cannot list USB devices directory: {e}")
                    return None

                for entry in entries:
                    if entry.startswith(hub_pattern + ".") and entry != device_name:
                        sibling_path = os.path.join(usb_devices_dir, entry)
                        log.debug(f"SDWireC: Found potential sibling: {entry}")
                        log.debug(f"SDWireC: Sibling full path: {sibling_path}")

                        if not os.path.isdir(sibling_path):
                            continue

                        # Check if this sibling is a mass storage device
                        try:
                            # Check bDeviceClass
                            class_file = os.path.join(sibling_path, "bDeviceClass")
                            if os.path.exists(class_file):
                                try:
                                    with open(class_file, "r") as f:
                                        device_class = f.read().strip()
                                        log.debug(f"SDWireC: Sibling {entry} has device class: {device_class}")
                                        # Mass storage class is 08
                                        if device_class == "08":
                                            log.debug(f"SDWireC: Found mass storage sibling: {sibling_path}")
                                            # Found mass storage sibling, look for its block device directly
                                            log.debug(f"SDWireC: Searching for block device in: {sibling_path}")
                                            block_device = _find_usb_mass_storage_block_device(sibling_path)
                                            if block_device:
                                                log.debug(f"SDWireC: Found block device: {block_device}")
                                                return block_device
                                            else:
                                                log.debug(f"SDWireC: No block device found in: {sibling_path}")
                                except (OSError, IOError) as e:
                                    log.debug(f"SDWireC: Error reading device class file: {e}")
                                    continue

                            # Also check interface class for composite devices
                            try:
                                sibling_items = os.listdir(sibling_path)
                            except (OSError, IOError):
                                continue

                            for item in sibling_items:
                                if item.startswith(entry + ":"):
                                    interface_path = os.path.join(sibling_path, item)
                                    class_file = os.path.join(interface_path, "bInterfaceClass")
                                    if os.path.exists(class_file):
                                        try:
                                            with open(class_file, "r") as f:
                                                interface_class = f.read().strip()
                                                log.debug(f"SDWireC: Interface {item} has class: {interface_class}")
                                                # Mass storage interface class is 08
                                                if interface_class == "08":
                                                    log.debug(f"SDWireC: Found mass storage interface in sibling: {sibling_path}")
                                                    log.debug(f"SDWireC: Searching for block device via interface in: {sibling_path}")
                                                    block_device = _find_usb_mass_storage_block_device(sibling_path)
                                                    if block_device:
                                                        log.debug(f"SDWireC: Found block device via interface: {block_device}")
                                                        return block_device
                                                    else:
                                                        log.debug(f"SDWireC: No block device found via interface in: {sibling_path}")
                                        except (OSError, IOError) as e:
                                            log.debug(f"SDWireC: Error reading interface class file: {e}")
                                            continue

                        except (OSError, ValueError, IOError) as e:
                            log.debug(f"SDWireC: Error checking sibling {entry}: {e}")
                            continue
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    except (TimeoutError, OSError, IOError) as e:
        log.debug(f"Error finding SDWireC block device: {e}")

    return None


def _search_block_devices_recursive(base_path: str) -> Optional[str]:
    """Recursively search for block devices under a USB device path."""
    return _search_block_devices_with_limits(base_path, max_depth=8, visited=set())


def _search_block_devices_with_limits(base_path: str, max_depth: int, visited: set) -> Optional[str]:
    """Recursively search for block devices with depth and cycle protection."""
    try:
        # Prevent infinite recursion
        if max_depth <= 0:
            log.debug(f"Max recursion depth reached for: {base_path}")
            return None

        # Get canonical path to handle symlinks properly
        try:
            canonical_path = os.path.realpath(base_path)
        except (OSError, IOError):
            canonical_path = base_path

        # Prevent cycles by tracking visited paths
        if canonical_path in visited:
            log.debug(f"Already visited path (cycle detected): {canonical_path}")
            return None

        visited.add(canonical_path)

        # Add timeout protection for recursive operations
        def timeout_handler(signum, frame):
            raise TimeoutError("Block device search timed out")

        # Set a 2 second timeout for this operation
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)

        try:
            # Check if base path still exists (device might be disconnected)
            if not os.path.exists(base_path):
                log.debug(f"Base path no longer exists: {base_path}")
                return None

            # Check if this directory has a block subdirectory
            block_path = os.path.join(base_path, "block")
            if os.path.exists(block_path):
                # List block devices in this directory
                try:
                    block_devices = os.listdir(block_path)
                    if block_devices:
                        # Return the first block device found
                        block_device = block_devices[0]
                        log.debug(f"Found block device: {block_device} in {block_path}")
                        return f"/dev/{block_device}"
                except (OSError, PermissionError, IOError):
                    pass

            # Search in subdirectories, with special handling for USB mass storage hierarchy
            try:
                if not os.path.exists(base_path):
                    return None

                items = os.listdir(base_path)
                # Sort to prioritize certain patterns (host, target, scsi devices)
                items.sort(key=lambda x: (
                    0 if x.startswith('host') else
                    1 if x.startswith('target') else
                    2 if ':' in x and x.replace(':', '').replace('.', '').isdigit() else
                    3
                ))

                # Limit the number of items to explore to prevent excessive recursion
                for item in items[:20]:  # Limit to first 20 items
                    item_path = os.path.join(base_path, item)

                    # Skip non-directories and hidden items
                    if not os.path.isdir(item_path) or item.startswith('.'):
                        continue

                    # Skip some common non-relevant directories for performance
                    if item in ['power', 'driver', 'subsystem', 'ep_00', 'uevent', 'modalias']:
                        continue

                    # Skip some obvious non-storage related paths (but be conservative)
                    if item in ['uevent', 'modalias', 'bConfigurationValue']:
                        continue

                    result = _search_block_devices_with_limits(item_path, max_depth - 1, visited.copy())
                    if result:
                        return result
            except (OSError, PermissionError, IOError):
                pass
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    except (TimeoutError, OSError, IOError) as e:
        log.debug(f"Error searching for block devices: {e}")

    return None




def _find_block_device_macos(usb_device: usb.core.Device) -> Optional[str]:
    """Find block device on macOS using system_profiler and diskutil."""
    try:
        # Get USB device info
        try:
            vendor_id = f"{getattr(usb_device, 'idVendor', 0):04x}"
            product_id = f"{getattr(usb_device, 'idProduct', 0):04x}"
        except (AttributeError, TypeError):
            log.debug("Could not access USB device vendor/product ID")
            return None

        # Use system_profiler to get USB device info
        result = subprocess.run(
            ["system_profiler", "SPUSBDataType", "-xml"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            log.debug("system_profiler command failed")
            return None

        # Parse the output to find our device
        # This is a simplified approach - in practice you might want to use plistlib
        output = result.stdout.lower()

        # Look for our device by vendor/product ID
        if vendor_id in output and product_id in output:
            # Try to find associated disk using diskutil
            disk_result = subprocess.run(
                ["diskutil", "list", "-plist"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if disk_result.returncode == 0:
                # Simple pattern matching for external disks
                # This could be improved with proper plist parsing
                lines = disk_result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if 'external' in line.lower() and 'physical' in line.lower():
                        # Look for disk identifier in nearby lines
                        for j in range(max(0, i-5), min(len(lines), i+5)):
                            match = re.search(r'/dev/(disk\d+)', lines[j])
                            if match:
                                return match.group(0)

    except Exception as e:
        log.debug(f"Error finding block device on macOS: {e}")

    return None


def _find_block_device_windows(usb_device: usb.core.Device) -> Optional[str]:
    """Find block device on Windows using WMI queries."""
    try:
        # This requires additional Windows-specific libraries
        # For now, return None and log a message
        log.info("Windows block device detection not yet implemented")
        log.info("Consider using 'wmi' library for full Windows support")

        # Placeholder implementation using diskpart
        # This is a basic approach and might need refinement
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-WmiObject -Class Win32_LogicalDisk | Where-Object {$_.DriveType -eq 2} | Select-Object DeviceID"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ':' in line and len(line.strip()) == 2:
                        # Return the first removable drive found
                        # This is a very basic heuristic
                        return line.strip()
        except Exception as e:
            log.debug(f"Windows diskpart query failed: {e}")

    except Exception as e:
        log.debug(f"Error finding block device on Windows: {e}")

    return None


def get_block_device_by_serial(serial_number: str) -> Optional[str]:
    """
    Alternative method to find block device by serial number.
    Useful when USB device object is not available.
    """
    system = platform.system().lower()

    if system == 'linux':
        return _get_block_device_by_serial_linux(serial_number)
    elif system == 'darwin':
        return _get_block_device_by_serial_macos(serial_number)
    elif system == 'windows':
        return _get_block_device_by_serial_windows(serial_number)

    return None


def _find_usb_mass_storage_block_device(usb_device_path: str) -> Optional[str]:
    """Find block device for USB mass storage device using direct path traversal."""
    try:
        # Add timeout protection for mass storage device search
        def timeout_handler(signum, frame):
            raise TimeoutError("USB mass storage search timed out")

        # Set a 2 second timeout for this operation
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)

        try:
            log.debug(f"Looking for mass storage block device in: {usb_device_path}")

            # Check if the device path still exists
            if not os.path.exists(usb_device_path):
                log.debug(f"USB device path no longer exists: {usb_device_path}")
                return None

            # For USB mass storage, follow the typical hierarchy:
            # device -> interface -> host -> target -> scsi_device -> block

            # Look for the mass storage interface (usually :1.0)
            for item in os.listdir(usb_device_path):
                if item.endswith(':1.0'):
                    interface_path = os.path.join(usb_device_path, item)
                    if not os.path.exists(interface_path):
                        continue
                    log.debug(f"Found interface: {interface_path}")

                    # Look for host directory
                    try:
                        for host_item in os.listdir(interface_path):
                            if host_item.startswith('host'):
                                host_path = os.path.join(interface_path, host_item)
                                if not os.path.exists(host_path):
                                    continue
                                log.debug(f"Found host: {host_path}")

                                # Look for target directory
                                try:
                                    for target_item in os.listdir(host_path):
                                        if target_item.startswith('target'):
                                            target_path = os.path.join(host_path, target_item)
                                            if not os.path.exists(target_path):
                                                continue
                                            log.debug(f"Found target: {target_path}")

                                            # Look for scsi device (format like "0:0:0:0")
                                            try:
                                                for scsi_item in os.listdir(target_path):
                                                    if ':' in scsi_item and scsi_item.replace(':', '').isdigit():
                                                        scsi_path = os.path.join(target_path, scsi_item)
                                                        if not os.path.exists(scsi_path):
                                                            continue
                                                        log.debug(f"Found SCSI device: {scsi_path}")

                                                        # Look for block directory
                                                        block_path = os.path.join(scsi_path, 'block')
                                                        if os.path.exists(block_path):
                                                            try:
                                                                block_devices = os.listdir(block_path)
                                                                if block_devices:
                                                                    block_device = block_devices[0]
                                                                    log.debug(f"Found block device: {block_device}")
                                                                    return f"/dev/{block_device}"
                                                            except (OSError, IOError):
                                                                continue
                                            except (OSError, IOError):
                                                continue
                                except (OSError, IOError):
                                    continue
                    except (OSError, IOError):
                        continue
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    except (TimeoutError, OSError, IOError) as e:
        log.debug(f"Error finding USB mass storage block device: {e}")

    return None


def _get_block_device_by_serial_linux(serial_number: str) -> Optional[str]:
    """Find block device by serial number on Linux."""
    try:
        # Check /dev/disk/by-id/ for serial-based links
        by_id_path = "/dev/disk/by-id/"
        if os.path.exists(by_id_path):
            for link in os.listdir(by_id_path):
                if serial_number in link:
                    link_path = os.path.join(by_id_path, link)
                    if os.path.islink(link_path):
                        target = os.readlink(link_path)
                        # Convert relative path to absolute
                        if not target.startswith('/'):
                            target = os.path.join(by_id_path, target)
                        return os.path.realpath(target)
    except Exception as e:
        log.debug(f"Error finding block device by serial on Linux: {e}")

    return None


def _get_block_device_by_serial_macos(serial_number: str) -> Optional[str]:
    """Find block device by serial number on macOS."""
    try:
        result = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Simple search for the serial number in output
            # This could be improved with proper plist parsing
            if serial_number in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    match = re.search(r'/dev/(disk\d+)', line)
                    if match:
                        return match.group(0)
    except Exception as e:
        log.debug(f"Error finding block device by serial on macOS: {e}")

    return None


def _get_block_device_by_serial_windows(serial_number: str) -> Optional[str]:
    """Find block device by serial number on Windows."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-WmiObject -Class Win32_PhysicalMedia | Where-Object {{$_.SerialNumber -eq '{serial_number}'}} | Select-Object Tag"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            # Extract physical drive identifier
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'PHYSICALDRIVE' in line.upper():
                    return f"\\\\.\\{line.strip()}"
    except Exception as e:
        log.debug(f"Error finding block device by serial on Windows: {e}")

    return None
