import pyudev
import serial

class USB_Device_Fingerprint(object):
    XBEE = ["0403", "6015"]
    TTL = ["1a86", "7523"]
    CC2530 = ["204", "64"]
    CC2531 = ["0451", "16a8"]

class USB_Device_Category(object):
    XBEE = 1
    TTL = 2
    CC2530 = 3
    CC2531 = 4

class USB_Device_Baud_Rate(object):
    XBEE = 57600
    TTL = 9600
    CC2530 = 57600
    CC2531 = 57600

class USB_Device(object):
    def __init__(self):
        self.path = None
        self.baud_rate = None
        self.category = None
        self.serial_object = None

class USB_Manager(object):
    def __init__(self):
        """
        Initialize the USB manager.
        """

        self._reset()

    def _reset(self):
        """
        Reset internal state of the USB manager index.

        Use `clear` to ensure all serial objects are closed.
        """

        self._devices = {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: [],
            USB_Device_Category.CC2530: [],
            USB_Device_Category.CC2531: []
        }

    def index(self):
        """
        Index all connected USB devices with their path, baud rate and category.
        """

        for device in self._obtain_usb_devices():
            fingerprint = [device["ID_VENDOR_ID"], device["ID_MODEL_ID"]]
            self._insert_device(device, fingerprint)

        for device in self._obtain_amba_devices():
            fingerprint = [device["MAJOR"], device["MINOR"]]
            self._insert_device(device, fingerprint)

    def _insert_device(self, device, fingerprint):
        """
        Identify a `device` using its `fingerprint` and insert it into the
        index of available USB/AMBA devices.
        """

        if fingerprint == USB_Device_Fingerprint.XBEE:
            baud_rate = USB_Device_Baud_Rate.XBEE
            category = USB_Device_Category.XBEE
        elif fingerprint == USB_Device_Fingerprint.TTL:
            baud_rate = USB_Device_Baud_Rate.TTL
            category = USB_Device_Category.TTL
        elif fingerprint == USB_Device_Fingerprint.CC2530:
            baud_rate = USB_Device_Baud_Rate.CC2530
            category = USB_Device_Category.CC2530
        elif fingerprint == USB_Device_Fingerprint.CC2531:
            baud_rate = USB_Device_Baud_Rate.CC2531
            category = USB_Device_Category.CC2531
        else:
            return

        usb_device = USB_Device()
        usb_device.path = device["DEVNAME"]
        usb_device.baud_rate = baud_rate
        usb_device.category = category

        self._devices[category].append(usb_device)

    def _obtain_usb_devices(self):
        """
        Obtain a list of available USB devices.
        """

        context = pyudev.Context()
        return list(context.list_devices(subsystem="tty", ID_BUS="usb"))

    def _obtain_amba_devices(self):
        """
        Obtain a list of available AMBA devices.
        """

        context = pyudev.Context()
        parents = context.list_devices(subsystem="amba")
        children = []
        for parent in parents:
            children = children + list(context.list_devices(subsystem="tty", parent=parent))

        return children

    def get_xbee_device(self, path=None):
        """
        Get the first available XBee device. If `path` is provided, get the
        XBee device with its path equal to `path`.
        """

        return self._get_device(USB_Device_Category.XBEE, path)

    def get_ttl_device(self, path=None):
        """
        Get the first available TTL device. If `path` is provided, get the
        TTL device with its path equal to `path`.
        """

        return self._get_device(USB_Device_Category.TTL, path)

    def get_cc2530_device(self, path=None):
        """
        Get the first available CC2530 device. If `path` is provided, get the
        CC2530 device with its path equal to `path`.
        """

        return self._get_device(USB_Device_Category.CC2530, path)

    def get_cc2531_device(self, path=None):
        """
        Get the first available CC2531 device. If `path` is provided, get the
        CC2531 device with its path equal to `path`.
        """

        return self._get_device(USB_Device_Category.CC2531, path)

    def _get_device(self, category, path):
        """
        Get the serial object of the first device for a given `category` in the
        device list. If `path` is provided, we get the serial object of the
        device at the given `path` for the given `category` instead. If a device
        is not found, a KeyError is raised.
        """

        # Get all devices for the category and stop when none are available.
        devices = self._devices[category]
        if len(devices) == 0:
            raise KeyError("No devices found.")

        # Set the first device as the default one. If a path is provided,
        # we override this default device.
        device = devices[0]
        if path is not None:
            found = False
            for override_device in devices:
                if override_device.path == path:
                    device = override_device
                    found = True
                    break

            if not found:
                raise KeyError("No device found at '{}'.".format(path))

        # Lazily initialize the serial object.
        if device.serial_object is None:
            device.serial_object = serial.Serial(
                device.path, device.baud_rate, rtscts=True, dsrdtr=True
            )

        # If the device was closed before but is still loaded in the USB 
        # manager, then reopen the connection.
        if not device.serial_object.isOpen():
            device.serial_object.open()

        return device.serial_object

    def clear(self):
        """
        Clear the list of USB devices and destroy any associated serial objects,
        canceling all operations and closing the connections.
        """

        for category in self._devices:
            for device in self._devices[category]:
                serial_object = device.serial_object
                if serial_object is not None and serial_object.isOpen():
                    serial_object.close()

        self._reset()
