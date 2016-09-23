# Core imports
import os
import unittest
from functools import partial

# Library imports
import serial
from mock import patch, Mock

# Package imports
from ..core.USB_Manager import USB_Manager, USB_Device_Category, USB_Device_Baud_Rate, USB_Device_Fingerprint

class USBManagerTestCase(unittest.TestCase):
    """
    A test case that makes use of a USB manager. We make sure that
    the USB manager contains a fixed number of devices instead of
    looking for the real devices.
    """

    @classmethod
    def _mock_list_devices(cls, usb_devices, amba_devices,
                           subsystem=None, parent=None, ID_BUS=None, **kwargs):
        if ID_BUS == "usb":
            return usb_devices

        if subsystem == "amba":
            return ["AMBA_PARENT"]

        if parent == "AMBA_PARENT":
            return amba_devices

        raise ValueError("Unexpected argument values: subsystem={}, parent={}, ID_BUS={}, {}".format(subsystem, parent, ID_BUS, kwargs))

    def _get_virtual_pty(self):
        master, slave = os.openpty()
        self._master_ptys.add(master)
        self._slave_ptys.add(slave)
        return master, slave

    def _close_virtual_ptys(self, ptys):
        for pty in ptys:
            # Only close virtual PTYs that are still open. Certain PTYs may be 
            # closed by the tearDown method, e.g., ones that were opened as 
            # files rather than left as file descriptors.
            if os.isatty(pty):
                os.close(pty)

    def setUp(self):
        super(USBManagerTestCase, self).setUp()

        # Initialize the USB manager.
        self.usb_manager = USB_Manager()

        # Create virtual serial ports for the mocked USB/AMBA devices.
        self._master_ptys = set()
        self._slave_ptys = set()
        self.addCleanup(self._close_virtual_ptys, self._master_ptys)
        self.addCleanup(self._close_virtual_ptys, self._slave_ptys)

        slave_xbee = self._get_virtual_pty()[1]
        self._xbee_port = os.ttyname(slave_xbee)

        master_ttl, slave_ttl = self._get_virtual_pty()
        self._ttl_device = os.fdopen(master_ttl, 'w+')
        self._ttl_port = os.ttyname(slave_ttl)

        slave_cc2530 = self._get_virtual_pty()[1]
        self._cc2530_port = os.ttyname(slave_cc2530)

        slave_cc2531 = self._get_virtual_pty()[1]
        self._cc2531_port = os.ttyname(slave_cc2531)

        slave_other = self._get_virtual_pty()[1]
        self._other_port = os.ttyname(slave_other)

        # Create a specific list of inserted USB devices.
        self._usb_devices = [
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
            { # CC2531 device
                "ID_VENDOR_ID": USB_Device_Fingerprint.CC2531[0],
                "ID_MODEL_ID": USB_Device_Fingerprint.CC2531[1],
                "DEVNAME": self._cc2531_port
            },
            { # Other device
                "ID_VENDOR_ID": "0402",
                "ID_MODEL_ID": "6012",
                "DEVNAME": self._other_port
            }
        ]

        # Create a specific list of detected AMBA devices.
        self._amba_devices = [
            { # CC2530 device
                "MAJOR": USB_Device_Fingerprint.CC2530[0],
                "MINOR": USB_Device_Fingerprint.CC2530[1],
                "DEVNAME": self._cc2530_port
            }
        ]

        # Mock the pyudev library to return the devices lists on specific 
        # argument input.
        list_devices_mock = Mock(side_effect=partial(self._mock_list_devices,
                                                     self._usb_devices, self._amba_devices))
        context_mock = Mock(list_devices=list_devices_mock)

        self._pyudev_patcher = patch('pyudev.Context', return_value=context_mock)
        self._pyudev_patcher.start()

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

        self._pyudev_patcher.stop()

        self._dtr_patcher.stop()
        self._rts_patcher.stop()

class TestCoreUSBManager(USBManagerTestCase):
    def test_initialization(self):
        # Initially the USB device storage must contain empty categories.
        self.assertEqual(self.usb_manager._devices, {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: [],
            USB_Device_Category.CC2530: [],
            USB_Device_Category.CC2531: []
        })

    def test_index(self):
        self.usb_manager.index()

        expected_index = {
            USB_Device_Category.XBEE: (self._xbee_port, USB_Device_Baud_Rate.XBEE),
            USB_Device_Category.TTL: (self._ttl_port, USB_Device_Baud_Rate.TTL),
            USB_Device_Category.CC2530: (self._cc2530_port, USB_Device_Baud_Rate.CC2530),
            USB_Device_Category.CC2531: (self._cc2531_port, USB_Device_Baud_Rate.CC2531)
        }

        # Valid devices should be indexed.
        for category, index in expected_index.iteritems():
            path, baud_rate = index
            devices = self.usb_manager._devices[category]
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0].path, path)
            self.assertEqual(devices[0].baud_rate, baud_rate)
            self.assertEqual(devices[0].category, category)
            self.assertIsNone(devices[0].serial_object)

    def check_get_device(self, method, path):
        """
        Helper function to test whether the method for obtaining a device
        works as expected.
        """

        # Getting a device should fail when there are none.
        with self.assertRaises(KeyError):
            device = method()

        self.usb_manager.index()

        # Now that there are devices, we should get a valid serial object.
        device = method()
        self.assertIsInstance(device, serial.Serial)

        # Overriding the path with a valid one gives us a valid serial object.
        device = method(path)
        self.assertIsInstance(device, serial.Serial)

        # Closing the device and retrieving it again reopens the connection.
        device.close()
        second_device = method(path)
        self.assertEqual(device, second_device)
        self.assertTrue(second_device.isOpen())

        # Overriding the path with an invalid one should result in an exception.
        with self.assertRaises(KeyError):
            device = method("/dev/tyUSB0")

    def test_get_xbee_device(self):
        self.check_get_device(self.usb_manager.get_xbee_device, self._xbee_port)

    def test_get_ttl_device(self):
        self.check_get_device(self.usb_manager.get_ttl_device, self._ttl_port)

    def test_get_cc2530_device(self):
        self.check_get_device(self.usb_manager.get_cc2530_device, self._cc2530_port)

    def test_get_cc2531_device(self):
        self.check_get_device(self.usb_manager.get_cc2531_device, self._cc2531_port)

    def test_clear(self):
        self.usb_manager.index()
        devices = self.usb_manager._devices
        self.usb_manager.clear()

        # The USB device storage must contain empty categories.
        self.assertEqual(self.usb_manager._devices, {
            USB_Device_Category.XBEE: [],
            USB_Device_Category.TTL: [],
            USB_Device_Category.CC2530: [],
            USB_Device_Category.CC2531: []
        })

        # All previous serial objects should be closed.
        for category in devices:
            for device in devices[category]:
                if device.serial_object is not None:
                    self.assertFalse(device.serial_object.isOpen())
