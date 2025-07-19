import logging
from typing import Optional
from pyftdi.ftdi import Ftdi
import usb.core
from sdwire.backend.device.usb_device import USBDevice, PortInfo
from sdwire.backend.block_device_utils import map_usb_device_to_block_device

log = logging.getLogger(__name__)


class SDWireC(USBDevice):
    __block_dev = None

    def __init__(self, port_info: PortInfo):
        super().__init__(port_info)
        # SDWireC uses hub topology: FTDI chip + mass storage as siblings
        # The block device detection will look for sibling mass storage device
        if self.usb_device:
            log.debug(f"SDWireC: Looking for block device for FTDI chip {self.serial_string}")
            try:
                storage_device = self.storage_device
                if storage_device is not None:
                    self.__block_dev = map_usb_device_to_block_device(storage_device)
                    log.debug(f"SDWireC: Found block device: {self.__block_dev}")
                else:
                    log.debug("SDWireC: No storage USB device available")
                    self.__block_dev = None
            except Exception as e:
                log.debug(f"SDWireC: Block device detection failed: {e}")
                self.__block_dev = None
        else:
            log.debug("SDWireC: No USB device available")
            self.__block_dev = None

    def __str__(self) -> str:
        block_dev_str = self.block_dev if self.block_dev is not None else "None"
        return f"{self.serial_string}\t[{self.product_string}::{self.manufacturer_string}]\t{block_dev_str}"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def block_dev(self) -> Optional[str]:
        return self.__block_dev

    @property
    def storage_device(self) -> Optional[usb.core.Device]:
        """Return the USB device that corresponds to the storage interface.

        For SDWireC, this is a sibling mass storage device under the same hub,
        not the FTDI device we control.

        Returns:
            usb.core.Device: The sibling mass storage USB device, or None if not found
        """
        if not self.usb_device:
            return None

        try:
            # Find sibling mass storage devices under the same hub
            if not hasattr(self.usb_device, 'port_numbers'):
                return None

            device_ports = self.usb_device.port_numbers  # type: ignore[attr-defined]
            if len(device_ports) < 2:  # Need at least hub + device port
                return None

            # Find all devices on the same bus
            bus = self.usb_device.bus
            devices_iter = usb.core.find(find_all=True, bus=bus)
            if devices_iter is None:
                return None
            all_devices = list(devices_iter)

            for candidate in all_devices:
                if candidate == self.usb_device:
                    continue

                if not hasattr(candidate, 'port_numbers'):
                    continue

                try:
                    candidate_ports = candidate.port_numbers  # type: ignore[attr-defined]
                except (AttributeError, usb.core.USBError):
                    continue

                # Check if they share the same parent (same port path except last element)
                if (len(candidate_ports) >= 2 and
                    len(device_ports) >= 2 and
                    candidate_ports[:-1] == device_ports[:-1]):

                    # Check if it's a mass storage device (ensure candidate is Device, not Configuration)
                    if isinstance(candidate, usb.core.Device) and self._is_mass_storage_device(candidate):
                        log.debug(f"SDWireC: Found sibling storage device: {candidate}")
                        return candidate

        except Exception as e:
            log.debug(f"SDWireC: Error finding sibling storage device: {e}")

        return None

    def _is_mass_storage_device(self, device: usb.core.Device) -> bool:
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

    def switch_ts(self) -> None:
        self._set_sdwire(1)

    def switch_dut(self) -> None:
        self._set_sdwire(0)

    def _set_sdwire(self, target: int) -> None:
        if not self.usb_device:
            log.error("USB device not available")
            import sys
            print("USB device not available")
            sys.exit(1)

        try:
            ftdi = Ftdi()
            ftdi.open_from_device(self.usb_device)
            log.info(f"Set CBUS to 0x{0xF0 | target:02X}")
            ftdi.set_bitmode(0xF0 | target, Ftdi.BitMode.CBUS)
            ftdi.close()
        except Exception as e:
            import sys

            log.debug("error while updating ftdi device: %s", e, exc_info=True)
            print("couldnt switch sdwire device")
            sys.exit(1)
