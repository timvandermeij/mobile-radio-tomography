import pyudev
import serial

class USB_Device_Fingerprint(object):
    XBEE = ["0403", "6015"]
    TTL = ["1a86", "7523"]

class USB_Device_Category(object):
    XBEE = 1
    TTL = 2

class USB_Device_Baud_Rate(object):
    XBEE = 57600
    TTL = 9600

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

        self._devices = {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: []
        }

    def index(self):
        """
        Index all connected USB devices with their path, baud rate and category.
        """

        for device in self._obtain_devices():
            fingerprint = [device["ID_VENDOR_ID"], device["ID_MODEL_ID"]]

            if fingerprint == USB_Device_Fingerprint.XBEE:
                baud_rate = USB_Device_Baud_Rate.XBEE
                category = USB_Device_Category.XBEE
            elif fingerprint == USB_Device_Fingerprint.TTL:
                baud_rate = USB_Device_Baud_Rate.TTL
                category = USB_Device_Category.TTL
            else:
                continue

            usb_device = USB_Device()
            usb_device.path = device["DEVNAME"]
            usb_device.baud_rate = baud_rate
            usb_device.category = category

            self._devices[category].append(usb_device)

    def _obtain_devices(self):
        """
        Obtain a list of available USB devices.
        """

        context = pyudev.Context()
        return context.list_devices(subsystem="tty", ID_BUS="usb")

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
                    # Abort any blocking read and write operations before 
                    # closing. This prevent confusing exceptions about bad file 
                    # descriptors. Often, clear is called at the end of 
                    # a program, and whether the program finished successfully 
                    # or not, we do not need to know whether the serial 
                    # connections were still blocked or not.
                    # The cancel_* methods are new in pyserial 3.1.0, and 
                    # before that the interrupted blocking read/writes were 
                    # more lenient with throwing exceptions.
                    if hasattr(serial_object, 'cancel_read'):
                        serial_object.cancel_read()
                    if hasattr(serial_object, 'cancel_write'):
                        serial_object.cancel_write()

                    serial_object.close()

        self._devices = {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: []
        }
