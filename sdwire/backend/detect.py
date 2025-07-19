import logging
from typing import List

from sdwire import constants
from sdwire.backend.device.sdwire import SDWire, SDWIRE_GENERATION_SDWIRE3
from sdwire.backend.device.sdwirec import SDWireC
from sdwire.backend.device.usb_device import PortInfo


import usb.core
import usb.util


log = logging.getLogger(__name__)


def get_sdwirec_devices() -> List[SDWireC]:
    try:
        found_devices = usb.core.find(find_all=True)
        if found_devices is None:
            devices = []
        else:
            devices = list(found_devices)
    except Exception as e:
        log.debug("Error finding USB devices: %s", e)
        return []

    if not devices:
        log.info("no usb devices found while searching for SDWireC..")
        return []

    device_list = []
    for device in devices:
        product = None
        serial = None
        manufacturer = None
        try:
            # Safe attribute access
            product = getattr(device, 'product', None)
            serial = getattr(device, 'serial_number', None)
            manufacturer = getattr(device, 'manufacturer', None)
        except Exception as e:
            log.debug(
                "not able to get usb product, serial_number and manufacturer information, err: %s",
                e,
            )

        # filter with product string to allow non Badger'd sdwire devices to be detected
        if product == constants.SDWIREC_PRODUCT_STRING:
            device_list.append(
                SDWireC(port_info=PortInfo(None, product, manufacturer, serial, device))
            )

    return device_list


def get_sdwire_devices() -> List[SDWire]:
    # Badgerd SDWire3
    # VID = 0bda PID = 0316
    # Badgerd SDWireC
    # VID = 0x04e8 PID = 0x6001
    result = []
    try:
        found_devices = usb.core.find(
            find_all=True,
            idVendor=constants.SDWIRE3_VID,
            idProduct=constants.SDWIRE3_PID
        )
        if found_devices is None:
            devices = []
        else:
            devices = list(found_devices)
    except Exception as e:
        log.debug("Error finding SDWire3 devices: %s", e)
        devices = []

    if not devices:
        log.info("no usb devices found while searching for SDWire..")
    else:
        for device in devices:
            product = None
            serial = None
            vendor = None
            bus = None
            address = None
            try:
                # Safe attribute access
                product = getattr(device, 'idProduct', None)
                vendor = getattr(device, 'idVendor', None)
                bus = getattr(device, 'bus', None)
                address = getattr(device, 'address', None)
                serial_num = getattr(device, 'serial_number', None) or "unknown"
                serial = f"{serial_num}:{bus}.{address}"
            except Exception as e:
                log.debug(
                    "not able to get usb product, serial_number and manufacturer information, err: %s",
                    e,
                )

            if product == constants.SDWIRE3_PID and vendor == constants.SDWIRE3_VID:
                result.append(
                    SDWire(
                        port_info=PortInfo(device, product, vendor, serial, device),
                        generation=SDWIRE_GENERATION_SDWIRE3,
                    )
                )

    # Search for legacy SDWireC devices
    legacy_devices = get_sdwirec_devices()

    return result + legacy_devices
