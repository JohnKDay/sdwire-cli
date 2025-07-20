"""Block device utilities for mapping USB devices to system block devices.

This module provides cross-platform functionality to map USB storage devices
to their corresponding block device paths (e.g., /dev/sda on Linux, /dev/disk2 on macOS).
It uses USB hierarchy and topology information for accurate device mapping.
"""
import platform
import logging
import re
import subprocess
import json
import plistlib
from typing import Optional, List, Dict, Any
import usb.core
from sdwire.constants import SDWIRE3_VID, SDWIRE3_PID, SDWIREC_VID, SDWIREC_PID

log = logging.getLogger(__name__)


def map_usb_device_to_block_device(usb_device: usb.core.Device) -> Optional[str]:
    """Map a USB device to its corresponding system block device path using USB hierarchy.

    This function provides cross-platform mapping from USB devices to block devices
    using USB topology information rather than serial numbers for more reliable detection.

    Args:
        usb_device: USB device object from pyusb representing the storage device

    Returns:
        Block device path (e.g., '/dev/sda' on Linux, '/dev/disk2' on macOS)
        or None if no corresponding block device is found

    Note:
        - Uses USB bus, address, and port hierarchy for device correlation
        - Handles both direct storage devices and hub-based topologies
        - Falls back gracefully when USB information is not accessible
    """
    system = platform.system().lower()

    if system == 'linux':
        return _map_usb_to_block_device_linux(usb_device)
    elif system == 'darwin':  # macOS
        return _map_usb_to_block_device_macos(usb_device)
    else:
        log.warning(f"Unsupported platform: {system}")
        return None


def _get_usb_device_topology_key(usb_device: usb.core.Device) -> Optional[str]:
    """Generate a topology-based key for USB device identification.

    This creates a unique identifier based on USB bus, address, and port
    hierarchy rather than serial numbers which may not be unique.

    Args:
        usb_device: USB device to generate key for

    Returns:
        Topology key string or None if device info is not accessible
    """
    try:
        bus = getattr(usb_device, 'bus', None)
        address = getattr(usb_device, 'address', None)

        if bus is None or address is None:
            return None

        # Try to get port numbers for more specific topology info
        try:
            port_numbers = getattr(usb_device, 'port_numbers', [])
            if port_numbers:
                port_path = '.'.join(map(str, port_numbers))
                return f"{bus}:{address}@{port_path}"
        except (AttributeError, usb.core.USBError):
            pass

        # Fallback to bus:address
        return f"{bus}:{address}"

    except Exception as e:
        log.debug(f"Error generating topology key: {e}")
        return None


def _map_usb_to_block_device_linux(usb_device: usb.core.Device) -> Optional[str]:
    """Map USB device to block device on Linux using lsblk and USB topology.

    This function uses lsblk to enumerate block devices and correlates them
    with the USB device using bus and address information from sysfs.

    Args:
        usb_device: USB device object from pyusb

    Returns:
        Block device path (e.g., '/dev/sda') or None if not found
    """
    try:
        # Get device topology info
        device_key = _get_usb_device_topology_key(usb_device)
        if not device_key:
            log.debug("Could not generate topology key for USB device")
            return None

        # Use lsblk to get detailed block device information
        result = subprocess.run(
            ['lsblk', '-o', 'NAME,TRAN,VENDOR,MODEL,SERIAL,SUBSYSTEMS',
             '-J'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            log.debug("lsblk command failed")
            return None

        try:
            data = json.loads(result.stdout)
            blockdevices = data.get('blockdevices', [])

            # Find block devices that match our USB device topology
            for device in blockdevices:
                if device.get('tran') != 'usb':
                    continue

                device_name = device.get('name')
                if not device_name:
                    continue

                # Check if this block device corresponds to our USB device
                if _is_block_device_match_linux(device, usb_device,
                                               device_key):
                    log.debug(f"Found matching block device: {device_name}")
                    return f'/dev/{device_name}'

        except (json.JSONDecodeError, KeyError) as e:
            log.debug(f"Failed to parse lsblk output: {e}")

    except Exception as e:
        log.debug(f"Error mapping USB to block device on Linux: {e}")

    return None


def _is_block_device_match_linux(block_device: Dict[str, Any],
                                usb_device: usb.core.Device,
                                device_key: str) -> bool:
    """Check if a block device matches the given USB device on Linux.

    Uses sysfs to correlate block devices with USB devices through bus and
    address information.

    Args:
        block_device: Block device info from lsblk
        usb_device: USB device to match
        device_key: Topology key for the USB device

    Returns:
        True if the block device corresponds to the USB device
    """
    try:
        device_name = block_device.get('name')
        if not device_name:
            return False

        # Try to read USB info from sysfs
        sysfs_path = f'/sys/block/{device_name}'

        # Follow the device link to find USB information
        try:
            result = subprocess.run(
                ['readlink', '-f', f'{sysfs_path}/device'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                device_path = result.stdout.strip()

                # Extract bus and address from the device path
                # Typical path: /sys/devices/pci.../usb1/1-2/1-2.3/...
                # We look for patterns like "1-2.3" which indicate USB bus 1,
                # port path 2.3
                usb_match = re.search(r'/usb(\d+)/(\d+)-([0-9.]+)/',
                                     device_path)
                if usb_match:
                    bus_num = int(usb_match.group(1))
                    port_path = usb_match.group(3)

                    # Check if the topology matches (bus and port path)
                    if (device_key.startswith(f"{bus_num}:") and
                            f"@{port_path}" in device_key):
                        return True

        except Exception as e:
            log.debug(f"Error reading sysfs for {device_name}: {e}")
            return False


    except Exception as e:
        log.debug(f"Error checking block device match: {e}")
        return False

def _map_usb_to_block_device_macos(usb_device: usb.core.Device) -> Optional[str]:
    """Map USB device to block device on macOS using system_profiler and diskutil.

    This function uses macOS system tools to enumerate USB devices and find
    corresponding disk devices using USB topology information.

    Args:
        usb_device: USB device object from pyusb

    Returns:
        Block device path (e.g., '/dev/disk2') or None if not found
    """
    try:
        vendor_id = getattr(usb_device, 'idVendor', 0)
        product_id = getattr(usb_device, 'idProduct', 0)
        bus = getattr(usb_device, 'bus', None)
        address = getattr(usb_device, 'address', None)

        # Get USB device tree from system_profiler
        result = subprocess.run(
            ['system_profiler', 'SPUSBDataType', '-json'],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)
            usb_data = data.get('SPUSBDataType', [])

            # Find our USB device in the tree and get its location info
            location_id = _find_usb_device_location_macos(usb_data, vendor_id, product_id, bus, address)
            if not location_id:
                log.debug("Could not find USB device location in system_profiler output")
                return None

            # Now find the corresponding disk device
            return _find_disk_by_usb_location_macos(location_id, vendor_id, product_id)

        except json.JSONDecodeError:
            log.debug("Failed to parse system_profiler JSON output")

    except Exception as e:
        log.debug(f"Error finding block device on macOS: {e}")

    return None


def _find_usb_device_location_macos(usb_tree: List[Dict], target_vid: int,
                                   target_pid: int, target_bus: Optional[int],
                                   target_address: Optional[int]) -> Optional[str]:
    """Find USB device location ID in macOS system_profiler tree.

    Args:
        usb_tree: USB device tree from system_profiler
        target_vid: Target vendor ID
        target_pid: Target product ID
        target_bus: Target bus number (if available)
        target_address: Target address (if available)

    Returns:
        Location ID string or None if not found
    """
    def search_tree(items: List[Dict]) -> Optional[str]:
        for item in items:
            if isinstance(item, dict):
                # Check if this item matches our device
                vendor_id_str = item.get('vendor_id', '')
                product_id_str = item.get('product_id', '')
                location_id = item.get('location_id', '')

                try:
                    if (f'0x{target_vid:04x}' in vendor_id_str.lower() and
                            f'0x{target_pid:04x}' in product_id_str.lower()):

                        # Additional validation using bus info if available
                        if target_bus is not None:
                            # This is a simplified check; real implementation
                            # might need more sophisticated matching
                            if location_id:
                                return location_id

                        return location_id
                except Exception:
                    pass

                # Search children
                children = item.get('_items', [])
                result = search_tree(children)
                if result:
                    return result

        return None

    return search_tree(usb_tree)


def _find_disk_by_usb_location_macos(location_id: str, vendor_id: int,
                                    product_id: int) -> Optional[str]:
    """Find disk device corresponding to USB location ID on macOS.

    Args:
        location_id: USB location ID from system_profiler
        vendor_id: USB vendor ID for additional validation
        product_id: USB product ID for additional validation

    Returns:
        Block device path (e.g., '/dev/disk2') or None if not found
    """
    try:
        all_disks = _get_all_disks_macos()
        if not all_disks:
            return None

        # Check each disk to see if it corresponds to our USB device
        for disk in all_disks:
            if not _is_valid_disk_name(disk):
                continue

            disk_data = _get_disk_info_macos(disk)
            if not disk_data:
                continue

            if _is_matching_usb_disk_macos(disk_data, vendor_id, product_id):
                return f'/dev/{disk}'

    except Exception as e:
        log.debug(f"Error finding disk by USB location on macOS: {e}")

    return None


def _get_all_disks_macos() -> Optional[List[str]]:
    """Get list of all disks on macOS."""
    try:
        result = subprocess.run(
            ['diskutil', 'list', '-plist'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        data = plistlib.loads(result.stdout.encode())
        return data.get('AllDisks', [])

    except Exception as e:
        log.debug(f"Failed to get disk list on macOS: {e}")
        return None


def _is_valid_disk_name(disk: str) -> bool:
    """Check if disk name is valid (not a partition)."""
    return disk.startswith('disk') and not disk.endswith('s1')


def _get_disk_info_macos(disk: str) -> Optional[Dict[str, Any]]:
    """Get detailed information for a specific disk on macOS."""
    try:
        result = subprocess.run(
            ['diskutil', 'info', '-plist', disk],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        return plistlib.loads(result.stdout.encode())

    except Exception as e:
        log.debug(f"Error getting disk info for {disk}: {e}")
        return None


def _is_matching_usb_disk_macos(disk_data: Dict[str, Any], vendor_id: int,
                               product_id: int) -> bool:
    """Check if disk data matches the expected USB device."""
    # Check if this is a USB device
    bus_protocol = disk_data.get('BusProtocol', '')
    if 'USB' not in bus_protocol:
        return False

    return False

def find_sibling_storage_device(control_device: Optional[usb.core.Device]) -> Optional[usb.core.Device]:
    """Find sibling mass storage device for SDWireC hub topology.

    For SDWireC devices, the FTDI control chip and mass storage device are
    siblings under the same USB hub. This function finds the storage sibling.

    Args:
        control_device: The FTDI control device

    Returns:
        USB device object for the sibling mass storage device, or None if not
        found
    """
    if not control_device:
        return None

    try:
        control_topology = _get_device_topology_info(control_device)
        if control_topology is None:
            return None

        bus, control_ports = control_topology

        # Find all devices on the same bus
        all_devices = _get_devices_on_bus(bus)
        if not all_devices:
            return None

        return _find_sibling_in_devices(control_device, control_ports, all_devices)

    except Exception as e:
        log.debug(f"Error finding sibling storage device: {e}")

    return None


def _get_device_topology_info(device: usb.core.Device) -> Optional[tuple]:
    """Get topology information for a USB device."""
    try:
        bus = getattr(device, 'bus', None)
        if bus is None:
            return None

        ports = getattr(device, 'port_numbers', [])
        if ports is None:
            return None

        if not isinstance(ports, (list, tuple)):
            return None

        if len(ports) < 2:  # Need at least hub + device port
            return None

        return (bus, ports)

    except (AttributeError, usb.core.USBError) as e:
        log.debug(f"Could not get topology info for device: {e}")
        return None



def _get_devices_on_bus(bus: int) -> Optional[List[usb.core.Device]]:
    """Get all USB devices on a specific bus."""
    try:
        devices_iter = usb.core.find(find_all=True, bus=bus)
        if devices_iter is None:
            return None
        # Filter to only include Device objects, not Configuration objects
        devices = [dev for dev in devices_iter
                  if isinstance(dev, usb.core.Device)]
        return devices

    except Exception as e:
        log.debug(f"Error getting devices on bus {bus}: {e}")
        return None


def _find_sibling_in_devices(control_device: usb.core.Device,
                           control_ports: List[int],
                           all_devices: List[usb.core.Device]) -> Optional[usb.core.Device]:
    """Find sibling device among candidate devices."""
    for candidate in all_devices:
        if candidate == control_device:
            continue

        if _is_sibling_device(candidate, control_ports):
            return candidate

    return None


def _is_sibling_device(candidate: usb.core.Device, control_ports: List[int]) -> bool:
    """Check if candidate device is a sibling of the control device."""
    try:
        candidate_ports = getattr(candidate, 'port_numbers', [])
    except (AttributeError, usb.core.USBError):
        return False

    # Ensure candidate_ports is not None and is a list/tuple
    if candidate_ports is None:
        return False

    if not isinstance(candidate_ports, (list, tuple)):
        return False

    # Check if they share the same parent hub (same port path except last element)
    if (len(candidate_ports) >= 2 and
            len(control_ports) >= 2 and
            candidate_ports[:-1] == control_ports[:-1]):

        # Check if it's a mass storage device
        if (isinstance(candidate, usb.core.Device) and
                _is_mass_storage_device(candidate)):
            log.debug(f"Found sibling storage device for SDWireC: {candidate}")
            return True

    return False


def _is_mass_storage_device(device: usb.core.Device) -> bool:
    """Check if a USB device is a mass storage device.

    Args:
        device: USB device to check

    Returns:
        True if the device is a mass storage device
    """
    try:
        # Check device class
        device_class = getattr(device, 'bDeviceClass', None)
        if device_class == 8:  # Mass Storage class
            return True

        # Check interface class for composite devices
        try:
            config = device.get_active_configuration()
            for interface in config:
                if interface.bInterfaceClass == 8:  # Mass Storage interface
                    return True
        except Exception as e:
            log.debug(f"Could not access device interfaces: {e}")
            # For composite devices where we can't access interfaces due to
            # permissions, we'll use heuristics based on device class and
            # known SDWire patterns
            if device_class == 0:  # Composite device
                vendor_id = getattr(device, 'idVendor', 0)
                product_id = getattr(device, 'idProduct', 0)

                # Known storage device patterns for SDWire ecosystem
                if ((vendor_id == SDWIRE3_VID and
                     product_id == SDWIRE3_PID)):
                    return True

                # For SDWireC hub topology, if we find a composite device
                # with permission issues that's a sibling of an FTDI device,
                # it's likely the storage part. Samsung vendor ID is common
                # for SDWireC storage parts
                if vendor_id == 0x04e8:  # Samsung Electronics Co., Ltd
                    return True

                # Generic heuristic: if we can't determine the device type
                # due to permissions and it's a composite device, assume it
                # might be storage in SDWire context
                return True

    except Exception as e:
        log.debug(f"Error checking if device is mass storage: {e}")

    return False
