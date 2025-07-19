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




def map_usb_device_to_block_device(usb_device: usb.core.Device) -> Optional[str]:
    """Simple USB device to block device mapping using lsblk.

    Args:
        usb_device: USB device object from pyusb

    Returns:
        Block device path (e.g., '/dev/sda') or None if not found
    """
    system = platform.system().lower()

    if system == 'linux':
        return _map_usb_to_block_device_linux_simple(usb_device)
    elif system == 'darwin':  # macOS
        return _find_block_device_macos(usb_device)
    else:
        log.warning(f"Unsupported platform: {system}")
        return None


def _map_usb_to_block_device_linux_simple(usb_device: usb.core.Device) -> Optional[str]:
    """Simple Linux USB device to block device mapping using lsblk."""
    try:
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

            # First, try direct serial matching
            try:
                usb_serial = getattr(usb_device, 'serial_number', None)
                if usb_serial:
                    for device in blockdevices:
                        if device.get('tran') != 'usb':
                            continue

                        device_serial = device.get('serial')
                        device_name = device.get('name')

                        if device_serial and device_name and device_serial in usb_serial:
                            log.debug(f"Found block device by serial matching: {device_name}")
                            return f'/dev/{device_name}'

                    # If we can access serial but found no matching block device, return None
                    log.debug("Serial accessible but no matching block device found")
                    return None
                else:
                    # No serial available, use exclusion method (for permission issues)
                    log.debug("No serial available, using exclusion method")
                    return _find_block_device_by_exclusion_simple(blockdevices)
            except Exception as e:
                log.debug(f"Serial access failed, trying exclusion method: {e}")
                # Fallback: Use exclusion method for devices without accessible serials
                return _find_block_device_by_exclusion_simple(blockdevices)

        except (json.JSONDecodeError, KeyError) as e:
            log.debug(f"Failed to parse lsblk output: {e}")

    except Exception as e:
        log.debug(f"Error mapping USB to block device: {e}")

    return None


def _find_block_device_by_exclusion_simple(blockdevices: list) -> Optional[str]:
    """Find block device by excluding known SDWire3 devices."""
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
                log.debug(f"Found block device by exclusion: {block_name}")
                return f'/dev/{block_name}'

    except Exception as e:
        log.debug(f"Error in exclusion method: {e}")

    return None




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
