import random
import serial
import struct
import time
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from mock import patch
from settings import SettingsTestCase
from ..core.Thread_Manager import Thread_Manager
from ..zigbee.XBee_CC2531_Sensor_Physical import XBee_CC2531_Sensor_Physical, CC2531_Packet
from ..zigbee.XBee_Packet import XBee_Packet
from ..settings import Arguments

class TestXBeeCC2531SensorPhysical(USBManagerTestCase, ThreadableTestCase, SettingsTestCase):
    def location_callback(self):
        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0)), random.randint(0, 5)

    def receive_callback(self, packet):
        pass

    def valid_callback(self, other_valid=None, other_id=None, other_index=None):
        return True

    def setUp(self):
        super(TestXBeeCC2531SensorPhysical, self).setUp()

        self.sensor_id = 1

        self.arguments = Arguments("settings.json", ["--port", self._xbee_port])
        self.settings = self.arguments.get_settings("xbee_sensor_physical")
        self.thread_manager = Thread_Manager()

        self.usb_manager.index()
        self.sensor = XBee_CC2531_Sensor_Physical(self.arguments, self.thread_manager,
                                                  self.usb_manager, self.location_callback,
                                                  self.receive_callback, self.valid_callback)
        self.sensor._id = self.sensor_id

    def tearDown(self):
        # Ensure the sensor is deactivated for tests that use `mock_setup` but 
        # do not deactivate it themselves.
        self.sensor.deactivate()

        super(TestXBeeCC2531SensorPhysical, self).tearDown()

    def mock_setup(self):
        """
        Mock the activation of the XBee sensor by setting it up and enabling
        various flags that skip join checks. This does not actually start the
        sensor loop thread.
        """

        # Set all status variables to True to avoid being stuck in
        # the join loops. We cannot test the join process in the unit tests.
        self.sensor._node_identifier_set = True
        self.sensor._address_set = True
        self.sensor._joined = True
        self.sensor._synchronized = True

        # The serial connection and sensor must be initialized.
        self.sensor.setup()
        self.sensor._active = True

    @patch.object(serial.Serial, "write")
    def test_setup(self, write_mock):
        self.mock_setup()

        # Check if the CC2531 serial connection is initialized and
        # if the configuration packet has been sent.
        self.assertIsInstance(self.sensor._cc2531_serial_connection, serial.Serial)
        write_mock.assert_called_once_with(struct.pack("<HH", CC2531_Packet.CONFIGURATION, self.sensor._id))

    @patch.object(serial.Serial, "write")
    def test_send(self, write_mock):
        self.mock_setup()

        # Check if a CC2531 TX packet for performing an RSSI measurement
        # has been sent to the other sensor in the network.
        self.sensor._send()
        write_mock.assert_called_with(struct.pack("<HH", CC2531_Packet.TX, 2))

    @patch.object(serial.Serial, "read")
    def test_process_rssi_broadcast_packet(self, read_mock):
        # Simulate a USB packet coming from the CC2531 dongle.
        read_mock.return_value = struct.pack("<Hh", 2, 42)

        # Simulate an RSSI broadcast packet coming from the other XBee.
        packet = XBee_Packet()
        packet.set("specification", "rssi_broadcast")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        packet.set("valid", True)
        packet.set("waypoint_index", 1)
        packet.set("sensor_id", 1)
        packet.set("timestamp", time.time())

        self.mock_setup()

        # Processing a USB packet and an RSSI broadcast packet from different
        # sources should not result in a ground station packet being created.
        self.sensor._process_rssi_broadcast_packet(packet)
        self.assertEqual(self.sensor._data, {})

        # Processing a USB packet and an RSSI broadcast packet from the same
        # source should result in a ground station packet being created.
        packet.set("sensor_id", 2)
        self.sensor._process_rssi_broadcast_packet(packet)
        self.assertNotEqual(self.sensor._data, {})
        self.assertEqual(self.sensor._data.values()[0].get("rssi"), 42)
