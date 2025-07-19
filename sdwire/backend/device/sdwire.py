import logging
from sdwire.backend.device.usb_device import USBDevice, PortInfo
from sdwire.backend.block_device_utils import find_block_device_for_usb

log = logging.getLogger(__name__)

SDWIRE_GENERATION_SDWIRE3 = 2


class SDWire(USBDevice):
    __block_dev = None

    def __init__(self, port_info: PortInfo, generation: int):
        super().__init__(port_info)
        self.generation = generation
        # SDWire3 has direct access to media controller (no hub topology)
        # The block device detection will look for block devices under this device
        if self.usb_device:
            log.debug(f"SDWire3: Looking for block device for media controller {self.serial_string}")
            try:
                self.__block_dev = find_block_device_for_usb(self.usb_device)
                log.debug(f"SDWire3: Found block device: {self.__block_dev}")
            except Exception as e:
                log.debug(f"SDWire3: Block device detection failed: {e}")
                self.__block_dev = None
        else:
            log.debug("SDWire3: No USB device available")
            self.__block_dev = None

    def switch_ts(self):
        if not self.usb_device:
            log.error("USB device not available")
            return

        try:
            self.usb_device.attach_kernel_driver(0)
            self.usb_device.reset()
        except Exception as e:
            log.debug(
                "not able to switch to ts mode. Device might be already in ts mode, err: %s",
                e,
            )

    def switch_dut(self):
        if not self.usb_device:
            log.error("USB device not available")
            return

        try:
            self.usb_device.detach_kernel_driver(0)
            self.usb_device.reset()
        except Exception as e:
            log.debug(
                "not able to switch to dut mode. Device might be already in dut mode, err: %s",
                e,
            )

    @property
    def block_dev(self):
        return self.__block_dev

    def __str__(self):
        block_dev_str = self.block_dev if self.block_dev is not None else "None"
        return f"{self.serial_string}\t[{int(self.manufacturer_string):04x}::{int(self.product_string):04x}]\t\t{block_dev_str}"

    def __repr__(self):
        return self.__str__()
