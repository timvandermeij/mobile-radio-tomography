import unittest
from ..zigbee.XBee_Packet import XBee_Packet
from ..reconstruction.Stream_Buffer import Stream_Buffer

class TestReconstructionStreamBuffer(unittest.TestCase):
    def test_initialization(self):
        # Stream buffers are regular buffers with the exception that they
        # use options to set the number of sensors, origin and size.
        # Verify that these are set correctly upon initialization.
        options = {
            "number_of_sensors": 42,
            "origin": [1, 1],
            "size": [15, 15],
            "calibrate": True
        }
        stream_buffer = Stream_Buffer(options)

        self.assertEqual(stream_buffer.number_of_sensors, options["number_of_sensors"])
        self.assertEqual(stream_buffer.origin, options["origin"])
        self.assertEqual(stream_buffer.size, options["size"])

    def test_get(self):
        packet = XBee_Packet()
        packet.set("specification", "rssi_ground_station")
        packet.set("sensor_id", 1)
        packet.set("from_latitude", 1)
        packet.set("from_longitude", 0)
        packet.set("from_valid", True)
        packet.set("to_latitude", 1)
        packet.set("to_longitude", 10)
        packet.set("to_valid", True)
        packet.set("rssi", -38)

        # If calibration mode is enabled, the original RSSI values must be fetched.
        options = {
            "number_of_sensors": 42,
            "origin": [1, 1],
            "size": [15, 15],
            "calibrate": True
        }
        stream_buffer = Stream_Buffer(options)
        stream_buffer.put(packet)

        buffer_packet = stream_buffer.get()
        self.assertEqual(buffer_packet.get("rssi"), -38)

        # If calibration mode is disabled, the calibrated RSSI values must be fetched.
        options = {
            "number_of_sensors": 42,
            "origin": [1, 1],
            "size": [15, 15],
            "calibrate": False,
            "calibration_file": "tests/reconstruction/stream_empty.json"
        }
        stream_buffer = Stream_Buffer(options)
        stream_buffer.put(packet)

        buffer_packet = stream_buffer.get()
        self.assertEqual(buffer_packet.get("rssi"), -38 - -34)
