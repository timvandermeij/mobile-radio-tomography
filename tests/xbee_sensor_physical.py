import unittest
import pty
import os
import serial
import random
import json
from xbee import ZigBee
from mock import patch
from ..settings import Arguments
from ..zigbee.XBee_Packet import XBee_Packet
from ..zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from ..zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical

class TestXBeeSensorPhysical(unittest.TestCase):
    def get_location(self):
        """
        Get the current GPS location (latitude and longitude pair).
        """

        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

    def setUp(self):
        self.sensor_id = 1

        # Create a virtual serial port.
        master, slave = pty.openpty()
        self.port = os.ttyname(slave)

        self.arguments = Arguments("settings.json", [
            "--port", self.port,
            "--sensors", "sensor_0", "sensor_1", "sensor_2"
        ])
        self.scheduler = XBee_TDMA_Scheduler(self.sensor_id, self.arguments)
        self.sensor = XBee_Sensor_Physical(self.sensor_id, self.arguments,
                                           self.scheduler, self.get_location)

    def test_initialization(self):
        self.assertEqual(self.sensor.id, self.sensor_id)
        self.assertEqual(self.sensor.scheduler, self.scheduler)
        self.assertTrue(hasattr(self.sensor._location_callback, "__call__"))
        self.assertTrue(self.sensor._next_timestamp > 0)
        self.assertEqual(self.sensor._serial_connection, None)
        self.assertEqual(self.sensor._sensor, None)
        self.assertEqual(self.sensor._address, None)
        self.assertEqual(self.sensor._data, {})
        self.assertEqual(self.sensor._node_identifier_set, False)

    def test_activate_and_deactivate(self):
        # The serial connection and sensor must be lazily initialized.
        self.sensor.activate()
        self.assertTrue(isinstance(self.sensor._serial_connection, serial.Serial))
        self.assertTrue(isinstance(self.sensor._sensor, ZigBee))

        # After deactivation the serial connection must be closed.
        # Note that this also means that the sensor is halted.
        self.sensor.deactivate()
        with self.assertRaises(serial.SerialException):
            self.sensor._send()

    @patch("xbee.ZigBee.send")
    def test_send(self, mock_send):
        self.sensor._address = "sensor_{}".format(self.sensor_id)

        # Activate the sensor and ignore any _send() calls as we are not
        # interested in the initialization calls.
        self.sensor.activate()
        mock_send.call_count = 0

        # Packets must be sent to all other sensors except the ground sensor
        # and itself. Since there are three sensors in the settings, one
        # packet is expected here.
        self.sensor._send()
        self.assertEqual(mock_send.call_count, 1)

        # If the data object contains valid packets (i.e., both packet and RSSI
        # value not None), then they must be sent to the ground station. We
        # expect 2 here as the first call originates from the call tested above
        # and the second call is for transmitting the only valid packet in the
        # data object below to the ground station. After transmission, the
        # packet should be removed from the data object.
        mock_send.call_count = 0
        valid = 42
        valid_packet = XBee_Packet()
        valid_packet.set("_rssi", valid)
        self.sensor._data = {
            12: None,
            16: XBee_Packet(),
            42: valid_packet
        }
        self.sensor._send()
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(self.sensor._data[valid], None)
        self.sensor.deactivate()

    def test_receive(self):
        self.sensor.activate()

        # Malformed RX packets should be dropped.
        raw_packet = {
            "id": "rx",
            "rf_data": "invalid"
        }
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._data, {})

        # Valid RX packets should be processed. Store the frame ID
        # for the DB call test following this test.
        data = {
            "_from_id": 2,
            "_timestamp": 123456
        }
        raw_packet = {
            "id": "rx",
            "rf_data": json.dumps(data)
        }
        self.sensor._receive(raw_packet)
        frame_id = None
        for key, value in self.sensor._data.iteritems():
            frame_id = key

        # Check if the destination exists and if it consists only of floats.
        original_packet = self.sensor._data[frame_id]
        to_location = original_packet.get("_to")
        self.assertTrue(to_location != None)
        self.assertTrue(all(type(number) == float for number in to_location))

        self.assertTrue(original_packet.get("_rssi") == None)
        self.assertTrue(original_packet.get("_from_id") == None)
        self.assertTrue(original_packet.get("_timestamp") == None)

        # AT response DB packets should be processed. The parsed RSSI value
        # should be placed in the original packet in the data object.
        raw_packet = {
            "id": "at_response",
            "frame_id": frame_id,
            "command": "DB",
            "parameter": "\x4E"
        }
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._data[frame_id].get("_rssi"), ord("\x4E"))

        # AT response SH packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "SH",
            "parameter": "high"
        }
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._address, "high")

        # If a low part is already present in the address, the high
        # part should be prepended.
        self.sensor._address = "low"
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._address, "highlow")

        # If the high part is already present in the address (due to
        # a repeated request), it should not be prepended again.
        self.sensor._address = "highlow"
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._address, "highlow")

        # AT response SL packets should be processed.
        self.sensor._address = None
        raw_packet = {
            "id": "at_response",
            "command": "SL",
            "parameter": "low"
        }
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._address, "low")

        # If a high part is already present in the address, the low
        # part should be appended.
        self.sensor._address = "high"
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._address, "highlow")

        # If the low part is already present in the address (due to
        # a repeated request), it should not be appended again.
        self.sensor._address = "highlow"
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor._address, "highlow")

        # AT response NI packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "NI",
            "parameter": "4"
        }
        self.sensor._receive(raw_packet)
        self.assertEqual(self.sensor.id, 4)
        self.assertEqual(self.sensor.scheduler.id, 4)
        self.assertEqual(self.sensor._node_identifier_set, True)

        self.sensor.deactivate()
