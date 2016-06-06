# Core imports
import os
import unittest

# Library imports
import serial
from mock import patch, MagicMock

# Package imports
from ..core.USB_Manager import USB_Manager, USB_Device_Category, USB_Device_Baud_Rate, USB_Device_Fingerprint

class USBManagerTestCase(unittest.TestCase):
    """
    A test case that makes use of a USB manager. We make sure that
    the USB manager contains a fixed number of devices instead of
    looking for the real devices.
    """

    def setUp(self):
        super(USBManagerTestCase, self).setUp()

        # Initialize the USB manager.
        self.usb_manager = USB_Manager()

        # Create a virtual serial port.
        slave_xbee = os.openpty()[1]
        self._xbee_port = os.ttyname(slave_xbee)
        master_ttl, slave_ttl = os.openpty()
        self._ttl_device = os.fdopen(master_ttl)
        self._ttl_port = os.ttyname(slave_ttl)
        slave_other = os.openpty()[1]
        self._other_port = os.ttyname(slave_other)

        # Mock the method for obtaining devices.
        mock_obtain_devices = MagicMock(return_value=[
            { # XBee device
                "ID_VENDOR_ID": USB_Device_Fingerprint.XBEE[0],
                "ID_MODEL_ID": USB_Device_Fingerprint.XBEE[1],
                "DEVNAME": self._xbee_port
            },
            { # TTL device
                "ID_VENDOR_ID": USB_Device_Fingerprint.TTL[0],
                "ID_MODEL_ID": USB_Device_Fingerprint.TTL[1],
                "DEVNAME": self._ttl_port
            },
            { # Other device
                "ID_VENDOR_ID": "0402",
                "ID_MODEL_ID": "6012",
                "DEVNAME": self._other_port
            }
        ])
        self.usb_manager._obtain_devices = mock_obtain_devices

        # Disable internal pySerial updates of the DTR state since they do not 
        # function correctly when the serial device is mocked as a virtual pty.
        self._dtr_patcher = patch.object(serial.Serial, '_update_dtr_state')
        self._dtr_patcher.start()
        self._rts_patcher = patch.object(serial.Serial, '_update_rts_state')
        self._rts_patcher.start()

    def tearDown(self):
        super(USBManagerTestCase, self).tearDown()

        self.usb_manager.clear()
        self._ttl_device.close()

        self._dtr_patcher.stop()
        self._rts_patcher.stop()

class TestCoreUSBManager(USBManagerTestCase):
    def test_initialization(self):
        # Initially the USB device storage must contain empty categories.
        self.assertEqual(self.usb_manager._devices, {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: []
        })

    def test_index(self):
        self.usb_manager.index()

        # Valid XBee devices should be indexed.
        self.assertEqual(len(self.usb_manager._devices[USB_Device_Category.XBEE]), 1)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].path,
                         self._xbee_port)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].baud_rate,
                         USB_Device_Baud_Rate.XBEE)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].category,
                         USB_Device_Category.XBEE)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].serial_object,
                         None)

        # Valid TTL devices should be indexed.
        self.assertEqual(len(self.usb_manager._devices[USB_Device_Category.TTL]), 1)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.TTL][0].path,
                         self._ttl_port)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.TTL][0].baud_rate,
                         USB_Device_Baud_Rate.TTL)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.TTL][0].category,
                         USB_Device_Category.TTL)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.TTL][0].serial_object,
                         None)

    def test_get_xbee_device(self):
        # Getting an XBee device should fail when there are none.
        with self.assertRaises(KeyError):
            xbee = self.usb_manager.get_xbee_device()

        self.usb_manager.index()

        # Now that there are XBee devices, we should be able to get a valid serial object.
        xbee = self.usb_manager.get_xbee_device()
        self.assertIsInstance(xbee, serial.Serial)

        # Overriding the path with a valid one should result in a valid serial object.
        xbee = self.usb_manager.get_xbee_device(self._xbee_port)
        self.assertIsInstance(xbee, serial.Serial)

        # Overriding the path with an invalid one should result in an exception.
        with self.assertRaises(KeyError):
            xbee = self.usb_manager.get_xbee_device("/dev/tyUSB0")

    def test_get_ttl_device(self):
        # Getting a TTL device should fail when there are none.
        with self.assertRaises(KeyError):
            ttl = self.usb_manager.get_ttl_device()

        self.usb_manager.index()

        # Now that there are TTL devices, we should be able to get a valid serial object.
        ttl = self.usb_manager.get_ttl_device()
        self.assertIsInstance(ttl, serial.Serial)

        # Overriding the path with a valid one should result in a valid serial object.
        ttl = self.usb_manager.get_ttl_device(self._ttl_port)
        self.assertIsInstance(ttl, serial.Serial)

        # Overriding the path with an invalid one should result in an exception.
        with self.assertRaises(KeyError):
            ttl = self.usb_manager.get_ttl_device("/dev/ttyUSB0")

    def test_clear(self):
        self.usb_manager.index()
        devices = self.usb_manager._devices
        self.usb_manager.clear()

        # The USB device storage must contain empty categories.
        self.assertEqual(self.usb_manager._devices, {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: []
        })

        # All previous serial objects should be closed.
        for category in devices:
            for device in devices[category]:
                if device.serial_object is not None:
                    self.assertFalse(device.serial_object.isOpen())
