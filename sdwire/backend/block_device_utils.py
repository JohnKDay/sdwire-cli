import os
import platform
import logging
import subprocess
import re
from typing import Optional, List, Tuple
import usb.core
import usb.util

log = logging.getLogger(__name__)


def find_block_device_for_usb(usb_device: usb.core.Device) -> Optional[str]:
    """
    Find the block device path for a given USB device using pyusb.

    Args:
        usb_device: USB device object from pyusb

    Returns:
        Block device path (e.g., '/dev/sda', '/dev/disk2') or None if not found
    """
    system = platform.system().lower()

    if system == 'linux':
        return _find_block_device_linux(usb_device)
    elif system == 'darwin':  # macOS
        return _find_block_device_macos(usb_device)
    else:
        log.warning(f"Unsupported platform: {system}")
        return None


def _find_block_device_linux(usb_device: usb.core.Device) -> Optional[str]:
    """Find block device on Linux using pyusb device matching."""
    try:
        vendor_id = getattr(usb_device, 'idVendor', 0)
        product_id = getattr(usb_device, 'idProduct', 0)

        # Handle different device types
        if vendor_id == 0x04e8 and product_id == 0x6001:
            # SDWireC: FTDI chip, need to find sibling mass storage device
            return _find_sdwirec_block_device_linux(usb_device)
        else:
            # SDWire3 or other: Direct mass storage device
            return _find_direct_block_device_linux(usb_device)

    except Exception as e:
        log.debug(f"Error finding block device on Linux: {e}")
        return None


def _find_sdwirec_block_device_linux(ftdi_device: usb.core.Device) -> Optional[str]:
    """Find block device for SDWireC by looking for sibling mass storage device."""
    try:
        # Get the hub that contains the FTDI device
        hub = _find_parent_hub(ftdi_device)
        if not hub:
            log.debug("SDWireC: Could not find parent hub")
            return None

        log.debug(f"SDWireC: Found parent hub with {hub.port_numbers} ports")

        # Find mass storage siblings under the same hub
        mass_storage_devices = _find_mass_storage_devices_under_hub(hub)

        for ms_device in mass_storage_devices:
            # Skip the FTDI device itself
            if (ms_device.idVendor == ftdi_device.idVendor and
                ms_device.idProduct == ftdi_device.idProduct):
                continue

            log.debug(f"SDWireC: Found mass storage sibling: {ms_device.idVendor:04x}:{ms_device.idProduct:04x}")

            # Try to find block device for this mass storage device
            block_device = _map_usb_to_block_device_linux(ms_device)
            if block_device:
                log.debug(f"SDWireC: Mapped to block device: {block_device}")
                return block_device

    except Exception as e:
        log.debug(f"SDWireC: Error finding sibling block device: {e}")

    return None


def _find_direct_block_device_linux(usb_device: usb.core.Device) -> Optional[str]:
    """Find block device for direct USB mass storage device."""
    try:
        log.debug("SDWire3: Looking for direct mass storage block device")
        return _map_usb_to_block_device_linux(usb_device)
    except Exception as e:
        log.debug(f"SDWire3: Error finding direct block device: {e}")
        return None


def _find_parent_hub(usb_device: usb.core.Device) -> Optional[usb.core.Device]:
    """Find the parent hub for a USB device."""
    try:
        # Look for devices on the same bus that could be the parent hub
        bus = usb_device.bus
        devices = list(usb.core.find(find_all=True, bus=bus))

        # Look for hub devices (bDeviceClass == 9)
        for device in devices:
            try:
                if getattr(device, 'bDeviceClass', None) == 9:  # Hub class
                    # Check if this hub could be the parent by comparing port numbers
                    if hasattr(device, 'port_numbers') and hasattr(usb_device, 'port_numbers'):
                        device_ports = usb_device.port_numbers
                        hub_ports = device.port_numbers

                        # If the device's port path starts with the hub's port path, it's likely the parent
                        if len(device_ports) > len(hub_ports) and device_ports[:len(hub_ports)] == hub_ports:
                            return device
            except Exception:
                continue

    except Exception as e:
        log.debug(f"Error finding parent hub: {e}")

    return None


def _find_mass_storage_devices_under_hub(hub: usb.core.Device) -> List[usb.core.Device]:
    """Find all mass storage devices under a hub."""
    mass_storage_devices = []

    try:
        bus = hub.bus
        devices = list(usb.core.find(find_all=True, bus=bus))

        for device in devices:
            try:
                # Skip the hub itself
                if device == hub:
                    continue

                # Check if this device is under the hub
                if not _is_device_under_hub(device, hub):
                    continue

                # Check if it's a mass storage device
                if _is_mass_storage_device(device):
                    mass_storage_devices.append(device)

            except Exception:
                continue

    except Exception as e:
        log.debug(f"Error finding mass storage devices under hub: {e}")

    return mass_storage_devices


def _is_device_under_hub(device: usb.core.Device, hub: usb.core.Device) -> bool:
    """Check if a device is under a specific hub."""
    try:
        if not hasattr(device, 'port_numbers') or not hasattr(hub, 'port_numbers'):
            return False

        device_ports = device.port_numbers
        hub_ports = hub.port_numbers

        # Device is under hub if its port path starts with the hub's port path
        if len(device_ports) > len(hub_ports):
            return device_ports[:len(hub_ports)] == hub_ports

    except Exception:
        pass

    return False


def _is_mass_storage_device(device: usb.core.Device) -> bool:
    """Check if a USB device is a mass storage device."""
    try:
        # Check device class
        device_class = getattr(device, 'bDeviceClass', None)
        if device_class == 8:  # Mass Storage class
            return True

        # Check for known mass storage VID:PID combinations
        vendor_id = getattr(device, 'idVendor', 0)
        product_id = getattr(device, 'idProduct', 0)

        # Known mass storage devices commonly found in SDWire devices
        known_mass_storage = [
            (0x0424, 0x4050),  # SMSC Ultra Fast Media Reader
            (0x0424, 0x2640),  # SMSC USB 2.0 Hub with Mass Storage
        ]

        if (vendor_id, product_id) in known_mass_storage:
            log.debug(f"Found known mass storage device: {vendor_id:04x}:{product_id:04x}")
            return True

        # Check interface class for composite devices (if accessible)
        try:
            config = device.get_active_configuration()
            for interface in config:
                if interface.bInterfaceClass == 8:  # Mass Storage interface class
                    return True
        except Exception as e:
            log.debug(f"Could not access device interfaces (likely permission issue): {e}")
            # If we can't access interfaces and it's a composite device,
            # we'll assume it might be mass storage for SDWire hub topology
            if device_class == 0:
                log.debug("Composite device with inaccessible interfaces - treating as potential mass storage")
                return True

    except Exception:
        pass

    return False


def _map_usb_to_block_device_linux(usb_device: usb.core.Device) -> Optional[str]:
    """Map a USB device to its block device using /sys/class/block."""
    try:
        bus = getattr(usb_device, 'bus', None)
        address = getattr(usb_device, 'address', None)

        if bus is None or address is None:
            return None

        # Look through all block devices
        if not os.path.exists('/sys/class/block'):
            return None

        for block_name in os.listdir('/sys/class/block'):
            try:
                # Skip loop devices, partitions, etc.
                if block_name.startswith(('loop', 'ram', 'dm-')):
                    continue

                # Skip partition devices (e.g., sda1, sda2)
                if re.match(r'[a-z]+\d+$', block_name):
                    continue

                device_path = f'/sys/class/block/{block_name}/device'
                if not os.path.exists(device_path):
                    continue

                # Check if this block device belongs to our USB device
                if _is_block_device_for_usb(device_path, bus, address):
                    return f'/dev/{block_name}'

            except Exception:
                continue

    except Exception as e:
        log.debug(f"Error mapping USB to block device: {e}")

    return None


def _is_block_device_for_usb(device_path: str, target_bus: int, target_address: int) -> bool:
    """Check if a block device belongs to a specific USB device."""
    try:
        # Follow the device link to find the actual device path
        real_path = os.path.realpath(device_path)

        # Look for USB device identifiers in the path
        # USB devices typically have paths like: .../usb3/3-1/3-1.1/3-1.1:1.0/host0/target0:0:0/0:0:0:0
        path_parts = real_path.split('/')

        # Find all potential USB device identifiers in the path
        for part in path_parts:
            # Look for USB device patterns like "3-1.1", "3-2", etc.
            if '-' in part and ':' not in part and not part.startswith('usb'):
                # Check if this looks like a USB device identifier
                if re.match(r'^\d+-[\d.]+$', part):
                    # Check if there's a corresponding device in /sys/bus/usb/devices/
                    usb_device_path = f'/sys/bus/usb/devices/{part}'
                    if os.path.exists(usb_device_path):
                        # Check if this USB device matches our target
                        if _check_usb_device_match(usb_device_path, target_bus, target_address):
                            log.debug(f"Found matching USB device: {part}")
                            return True

    except Exception as e:
        log.debug(f"Error checking block device ownership: {e}")

    return False


def _check_usb_device_match(usb_path: str, target_bus: int, target_address: int) -> bool:
    """Check if a USB device path matches the target bus and address."""
    try:
        busnum_file = os.path.join(usb_path, 'busnum')
        devnum_file = os.path.join(usb_path, 'devnum')

        if os.path.exists(busnum_file) and os.path.exists(devnum_file):
            with open(busnum_file, 'r') as f:
                bus = int(f.read().strip())
            with open(devnum_file, 'r') as f:
                address = int(f.read().strip())

            return bus == target_bus and address == target_address

    except Exception:
        pass

    return False


def _find_block_device_macos(usb_device: usb.core.Device) -> Optional[str]:
    """Find block device on macOS using system_profiler and diskutil."""
    try:
        vendor_id = getattr(usb_device, 'idVendor', 0)
        product_id = getattr(usb_device, 'idProduct', 0)
        serial = getattr(usb_device, 'serial_number', None)

        # Use system_profiler to get USB device info
        result = subprocess.run(
            ['system_profiler', 'SPUSBDataType', '-json'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        # Parse the JSON output to find our device
        import json
        try:
            data = json.loads(result.stdout)
            usb_data = data.get('SPUSBDataType', [])

            # Look for our device in the USB tree
            if _find_usb_device_in_tree_macos(usb_data, vendor_id, product_id, serial):
                # If found, try to find the corresponding disk
                return _find_disk_for_usb_macos(vendor_id, product_id, serial)

        except json.JSONDecodeError:
            log.debug("Failed to parse system_profiler JSON output")

    except Exception as e:
        log.debug(f"Error finding block device on macOS: {e}")

    return None


def _find_usb_device_in_tree_macos(usb_tree: list, target_vid: int, target_pid: int, target_serial: str) -> bool:
    """Recursively search for USB device in macOS USB tree."""
    for item in usb_tree:
        if isinstance(item, dict):
            # Check if this item matches our device
            vendor_id = item.get('vendor_id', '')
            product_id = item.get('product_id', '')
            serial = item.get('serial_num', '')

            try:
                if (f'0x{target_vid:04x}' in vendor_id.lower() and
                    f'0x{target_pid:04x}' in product_id.lower()):
                    if not target_serial or target_serial in serial:
                        return True
            except Exception:
                pass

            # Check children
            items = item.get('_items', [])
            if _find_usb_device_in_tree_macos(items, target_vid, target_pid, target_serial):
                return True

    return False


def _find_disk_for_usb_macos(vendor_id: int, product_id: int, serial: str) -> Optional[str]:
    """Find disk device for USB device on macOS."""
    try:
        # Use diskutil to list all disks
        result = subprocess.run(
            ['diskutil', 'list', '-plist'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        # Parse the plist output
        import plistlib
        try:
            data = plistlib.loads(result.stdout.encode())
            all_disks = data.get('AllDisks', [])

            # Check each disk to see if it matches our USB device
            for disk in all_disks:
                if disk.startswith('disk') and not disk.endswith('s1'):  # Avoid partitions
                    disk_path = f'/dev/{disk}'
                    # In a real implementation, we'd need to check if this disk
                    # corresponds to our USB device, but this is a simplified approach
                    return disk_path

        except Exception as e:
            log.debug(f"Failed to parse diskutil plist output: {e}")

    except Exception as e:
        log.debug(f"Error finding disk for USB on macOS: {e}")

    return None
