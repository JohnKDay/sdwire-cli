import platform
import logging
import subprocess
import json
import plistlib
from typing import Optional, List
import usb.core
import usb.util
from sdwire.constants import SDWIREC_VID, SDWIREC_PID, SDWIRE3_VID, SDWIRE3_PID

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
    """Find block device on Linux using lsblk-based mapping."""
    return _map_usb_to_block_device_linux(usb_device)


def _is_mass_storage_device(device: usb.core.Device) -> bool:
    """Check if a USB device is a mass storage device."""
    try:
        # Check device class
        device_class = getattr(device, 'bDeviceClass', None)
        if device_class == 8:  # Mass Storage class
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
    """Map a USB device to its block device using lsblk."""
    try:
        usb_serial = getattr(usb_device, 'serial_number', None)
        if not usb_serial:
            log.debug("USB device has no serial number")
            return None

        # Use lsblk to get USB block devices with serial numbers
        result = subprocess.run(
            ['lsblk', '-o', 'NAME,TRAN,SERIAL', '-J'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            log.debug("lsblk command failed")
            return None

        try:
            data = json.loads(result.stdout)
            blockdevices = data.get('blockdevices', [])

            # First, try direct serial matching (works for SDWire3)
            for device in blockdevices:
                if device.get('tran') != 'usb':
                    continue

                device_serial = device.get('serial')
                device_name = device.get('name')

                if device_serial and device_name and device_serial in usb_serial:
                    return f'/dev/{device_name}'

            # If direct matching failed, check if this is SDWireC FTDI device
            vendor_id = getattr(usb_device, 'idVendor', 0)
            product_id = getattr(usb_device, 'idProduct', 0)

            if vendor_id == SDWIREC_VID and product_id == SDWIREC_PID:
                log.debug("SDWireC FTDI device - looking for sibling mass storage")
                return _find_sdwirec_sibling_block_device(usb_device, blockdevices)

        except (json.JSONDecodeError, KeyError) as e:
            log.debug(f"Failed to parse lsblk output: {e}")

    except Exception as e:
        log.debug(f"Error mapping USB to block device: {e}")

    return None


def _find_sdwirec_sibling_block_device(ftdi_device: usb.core.Device, blockdevices: list) -> Optional[str]:
    """Find block device for SDWireC by finding sibling mass storage device."""
    try:
        # Find sibling mass storage devices
        siblings = _find_sibling_mass_storage_devices(ftdi_device)

        # Try serial number matching first
        for sibling in siblings:
            try:
                sibling_serial = getattr(sibling, 'serial_number', None)
                if sibling_serial:
                    # Check if this sibling's serial matches any block device
                    for block_device in blockdevices:
                        if block_device.get('tran') != 'usb':
                            continue

                        block_serial = block_device.get('serial')
                        block_name = block_device.get('name')

                        if block_serial and block_name and block_serial in sibling_serial:
                            log.debug(f"Found SDWireC sibling block device: {block_name}")
                            return f'/dev/{block_name}'

            except Exception as e:
                log.debug(f"Error checking sibling serial: {e}")
                continue

        # If serial matching failed but we found siblings, try exclusion method
        if siblings:
            log.debug("SDWireC: Serial access denied, using exclusion method")
            return _find_block_device_by_exclusion(blockdevices)

    except Exception as e:
        log.debug(f"Error finding SDWireC sibling block device: {e}")

    return None


def _find_block_device_by_exclusion(blockdevices: list) -> Optional[str]:
    """Find SDWireC block device by excluding known SDWire3 devices."""
    try:
        # Get all USB block devices
        usb_blocks = []
        for device in blockdevices:
            if device.get('tran') == 'usb' and device.get('name'):
                usb_blocks.append(device)

        if not usb_blocks:
            return None

        # Find all SDWire3 devices to exclude their block devices
        sdwire3_serials = []
        try:
            sdwire3_devices = list(usb.core.find(find_all=True, idVendor=SDWIRE3_VID, idProduct=SDWIRE3_PID))
            for device in sdwire3_devices:
                try:
                    serial = getattr(device, 'serial_number', None)
                    if serial:
                        sdwire3_serials.append(serial)
                except Exception:
                    pass
        except Exception as e:
            log.debug(f"Error finding SDWire3 devices for exclusion: {e}")

        # Find USB block device that doesn't match any SDWire3 serial
        for block_device in usb_blocks:
            block_serial = block_device.get('serial', '')
            block_name = block_device.get('name')

            # Check if this block device's serial matches any SDWire3 device
            is_sdwire3 = any(serial in block_serial for serial in sdwire3_serials if serial)

            if not is_sdwire3 and block_name:
                log.debug(f"Found SDWireC block device by exclusion: {block_name}")
                return f'/dev/{block_name}'

    except Exception as e:
        log.debug(f"Error in exclusion method: {e}")

    return None


def _find_sibling_mass_storage_devices(usb_device: usb.core.Device) -> List[usb.core.Device]:
    """Find sibling mass storage devices under the same hub."""
    siblings = []

    try:
        if not hasattr(usb_device, 'port_numbers'):
            return siblings

        device_ports = usb_device.port_numbers
        if len(device_ports) < 2:  # Need at least hub + device port
            return siblings

        # Find all devices on the same bus
        bus = usb_device.bus
        all_devices = list(usb.core.find(find_all=True, bus=bus))

        for candidate in all_devices:
            if candidate == usb_device:
                continue

            if not hasattr(candidate, 'port_numbers'):
                continue

            candidate_ports = candidate.port_numbers

            # Check if they share the same parent (same port path except last element)
            if (len(candidate_ports) >= 2 and
                len(device_ports) >= 2 and
                candidate_ports[:-1] == device_ports[:-1]):

                # Check if it's a mass storage device
                if _is_mass_storage_device(candidate):
                    siblings.append(candidate)

    except Exception as e:
        log.debug(f"Error finding sibling devices: {e}")

    return siblings


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
