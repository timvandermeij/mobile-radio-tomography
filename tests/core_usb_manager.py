import os
import pty
import serial
import unittest
from mock import MagicMock
from ..core.USB_Manager import USB_Manager, USB_Device_Category, USB_Device_Baud_Rate

class TestCoreUSBManager(unittest.TestCase):
    def setUp(self):
        # Initialize the USB manager.
        self.usb_manager = USB_Manager()

        # Create a virtual serial port.
        master, slave = pty.openpty()
        self.port = os.ttyname(slave)

        # Mock the method for obtaining devices.
        mock_obtain_devices = MagicMock(return_value=[
            { # XBee device
                "ID_VENDOR_ID": "0403",
                "ID_MODEL_ID": "6015",
                "DEVNAME": self.port
            },
            { # TTL device
                "ID_VENDOR_ID": "0403",
                "ID_MODEL_ID": "6001",
                "DEVNAME": self.port
            },
            { # Other device
                "ID_VENDOR_ID": "0402",
                "ID_MODEL_ID": "6012",
                "DEVNAME": self.port
            }
        ])
        self.usb_manager._obtain_devices = mock_obtain_devices

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
                         self.port)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].baud_rate,
                         USB_Device_Baud_Rate.XBEE)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].category,
                         USB_Device_Category.XBEE)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.XBEE][0].serial_object,
                         None)

        # Valid TTL devices should be indexed.
        self.assertEqual(len(self.usb_manager._devices[USB_Device_Category.TTL]), 1)
        self.assertEqual(self.usb_manager._devices[USB_Device_Category.TTL][0].path,
                         self.port)
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
        xbee = self.usb_manager.get_xbee_device(self.port)
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
        ttl = self.usb_manager.get_ttl_device(self.port)
        self.assertIsInstance(ttl, serial.Serial)

        # Overriding the path with an invalid one should result in an exception.
        with self.assertRaises(KeyError):
            ttl = self.usb_manager.get_ttl_device("/dev/ttyUSB0")

    def test_clear(self):
        self.usb_manager.index()

        devices = self.usb_manager._devices
        xbee = self.usb_manager.get_xbee_device()

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
