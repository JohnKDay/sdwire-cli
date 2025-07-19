import logging
from pyftdi.ftdi import Ftdi
from .usb_device import USBDevice, PortInfo
from ..block_device_utils import find_block_device_for_usb

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
                self.__block_dev = find_block_device_for_usb(self.usb_device)
                log.debug(f"SDWireC: Found block device: {self.__block_dev}")
            except Exception as e:
                log.debug(f"SDWireC: Block device detection failed: {e}")
                self.__block_dev = None
        else:
            log.debug("SDWireC: No USB device available")
            self.__block_dev = None

    def __str__(self):
        block_dev_str = self.block_dev if self.block_dev is not None else "None"
        return f"{self.serial_string}\t[{self.product_string}::{self.manufacturer_string}]\t{block_dev_str}"

    def __repr__(self):
        return self.__str__()

    @property
    def block_dev(self):
        return self.__block_dev

    def switch_ts(self):
        self._set_sdwire(1)

    def switch_dut(self):
        self._set_sdwire(0)

    def _set_sdwire(self, target):
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
