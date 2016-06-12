# Core imports
import Queue
import time

# Library imports
from mock import patch, MagicMock, PropertyMock

# Package imports
from ..core.Thread_Manager import Thread_Manager
from ..settings.Arguments import Arguments
from ..reconstruction.Buffer import Buffer
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import RF_Sensor
from ..zigbee.TDMA_Scheduler import TDMA_Scheduler
from settings import SettingsTestCase

class TestZigBeeRFSensor(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", ["--rf-sensor-id", "1"])
        self.settings = self.arguments.get_settings("zigbee_base")

        self.thread_manager = Thread_Manager()
        self.location_callback = MagicMock(return_value=((0, 0), 0))
        self.receive_callback = MagicMock()
        self.valid_callback = MagicMock(return_value=True)

        type_mock = PropertyMock(return_value="zigbee_base")
        with patch.object(RF_Sensor, "type", new_callable=type_mock):
            self.rf_sensor = RF_Sensor(self.arguments, self.thread_manager,
                                       self.location_callback,
                                       self.receive_callback,
                                       self.valid_callback)

    def test_initialization(self):
        # Providing an uncallable callback raises an exception.
        with self.assertRaises(TypeError):
            RF_Sensor(self.arguments, self.thread_manager, None, None, None)

        # Not providing an `Arguments` object raises an exception.
        with self.assertRaises(ValueError):
            RF_Sensor(None, self.thread_manager, self.location_callback,
                      self.receive_callback, self.valid_callback)

        # The settings must be loaded when an `Arguments` object is provided.
        self.assertEqual(self.rf_sensor._settings, self.settings)

        # Common member variables must be initialized.
        self.assertEqual(self.rf_sensor._id, self.settings.get("rf_sensor_id"))
        self.assertEqual(self.rf_sensor._number_of_sensors,
                         self.settings.get("number_of_sensors"))
        self.assertEqual(self.rf_sensor._address, None)
        self.assertEqual(self.rf_sensor._connection, None)
        self.assertEqual(self.rf_sensor._buffer, None)
        self.assertIsInstance(self.rf_sensor._scheduler, TDMA_Scheduler)
        self.assertEqual(self.rf_sensor._scheduler_next_timestamp, 0)
        self.assertEqual(self.rf_sensor._packets, [])
        self.assertIsInstance(self.rf_sensor._queue, Queue.Queue)
        self.assertEqual(self.rf_sensor._queue.qsize(), 0)

        self.assertEqual(self.rf_sensor._joined, False)
        self.assertEqual(self.rf_sensor._activated, False)
        self.assertEqual(self.rf_sensor._started, False)

        self.assertEqual(self.rf_sensor._loop_delay, self.settings.get("loop_delay"))
        self.assertEqual(self.rf_sensor._custom_packet_delay,
                         self.settings.get("custom_packet_delay"))

        self.assertTrue(hasattr(self.rf_sensor._location_callback, "__call__"))
        self.assertTrue(hasattr(self.rf_sensor._receive_callback, "__call__"))
        self.assertTrue(hasattr(self.rf_sensor._valid_callback, "__call__"))

    def test_id(self):
        # The RF sensor ID must be returned.
        self.assertEqual(self.rf_sensor.id, self.rf_sensor._id)

    def test_number_of_sensors(self):
        # The number of sensors must be returned.
        self.assertEqual(self.rf_sensor.number_of_sensors,
                         self.rf_sensor._number_of_sensors)

    def test_buffer(self):
        # Providing an invalid buffer raises an exception.
        with self.assertRaises(ValueError):
            self.rf_sensor.buffer = []

        # A valid buffer must be set and returned.
        buffer = Buffer(self.settings)
        self.rf_sensor.buffer = buffer
        self.assertEqual(self.rf_sensor.buffer, buffer)

    def test_type(self):
        # Verify that the interface requires subclasses to implement
        # the `type` property.
        with self.assertRaises(NotImplementedError):
            dummy = self.rf_sensor.type

    def test_identity(self):
        # The identity must include the ID, address and network join status.
        self.assertEqual(self.rf_sensor.identity, {
            "id": self.rf_sensor._id,
            "address": self.rf_sensor._address,
            "joined": self.rf_sensor._joined
        })

    def test_start(self):
        # The sensor must be started for sending RSSI broadcast/ground
        # station packets.
        self.rf_sensor.start()
        self.assertEqual(self.rf_sensor._started, True)

    def test_stop(self):
        # The sensor must be stopped for sending custom packets.
        self.rf_sensor.stop()
        self.assertEqual(self.rf_sensor._started, False)

    def test_enqueue(self):
        packet = Packet()

        # Providing a packet that is not a `Packet` object raises an exception.
        with self.assertRaises(TypeError):
            self.rf_sensor.enqueue({
                "foo": "bar"
            })

        # Providing a private packet raises an exception.
        with self.assertRaises(ValueError):
            packet.set("specification", "rssi_broadcast")
            self.rf_sensor.enqueue(packet)

        # Packets that do not have a destination must be broadcasted.
        # We subtract one because we do not send to ourself.
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 2)
        self.rf_sensor.enqueue(packet)

        self.assertEqual(self.rf_sensor._queue.qsize(),
                         self.rf_sensor.number_of_sensors - 1)
        for to_id in xrange(1, self.rf_sensor.number_of_sensors + 1):
            if to_id == self.rf_sensor.id:
                continue

            item = self.rf_sensor._queue.get()
            self.assertIsInstance(item["packet"], Packet)
            self.assertEqual(item["packet"].get_all(), {
                "specification": "waypoint_clear",
                "to_id": 2
            })
            self.assertEqual(item["to"], to_id)

        self.assertEqual(self.rf_sensor._queue.qsize(), 0)

        # Packets that do contain a destination must be enqueued directly.
        self.rf_sensor.enqueue(packet, to=2)

        self.assertEqual(self.rf_sensor._queue.qsize(), 1)
        self.assertEqual(self.rf_sensor._queue.get(), {
            "packet": packet,
            "to": 2
        })
        self.assertEqual(self.rf_sensor._queue.qsize(), 0)

    def test_discover(self):
        # Providing an invalid callback raises an exception.
        with self.assertRaises(TypeError):
            self.rf_sensor.discover(None)

    def test_setup(self):
        # Verify that the interface requires subclasses to implement
        # the `_setup` method.
        with self.assertRaises(NotImplementedError):
            self.rf_sensor._setup()

    def test_loop(self):
        # Verify that the interface requires subclasses to implement
        # the `_loop` method.
        with self.assertRaises(NotImplementedError):
            self.rf_sensor._loop()

    def test_send(self):
        self.rf_sensor._packets.append(self.rf_sensor._create_rssi_broadcast_packet())

        with patch.object(RF_Sensor, "_send_tx_frame") as send_tx_frame_mock:
            self.rf_sensor._send()

            calls = send_tx_frame_mock.call_args_list

            # RSSI broadcast packets must be sent to all sensors in the network
            # (excluding ourself). Note that we do not inspect the packet contents
            # other than the specification because that is covered in the test
            # for the `_create_rssi_broadcast_packet` method.
            for to_id in xrange(1, self.rf_sensor.number_of_sensors + 1):
                if to_id == self.rf_sensor.id:
                    continue

                packet, to = calls.pop(0)[0]
                self.assertIsInstance(packet, Packet)
                self.assertEqual(packet.get("specification"), "rssi_broadcast")
                self.assertEqual(to, to_id)

            # RSSI ground station packets must be sent to the ground station.
            # The packet list must be empty afterwards. We added one packet to the
            # list at the start of this test, so we must detect it here.
            packet, to = calls.pop(0)[0]
            self.assertIsInstance(packet, Packet)
            self.assertEqual(packet.get("specification"), "rssi_broadcast")
            self.assertEqual(to, 0)

            self.assertEqual(self.rf_sensor._packets, [])

    def test_send_custom_packets(self):
        packet = Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 2)
        self.rf_sensor.enqueue(packet, to=2)

        with patch.object(RF_Sensor, "_send_tx_frame") as send_tx_frame_mock:
            self.rf_sensor._send_custom_packets()

            # Custom packets must be sent to their destinations.
            packet, to = send_tx_frame_mock.call_args[0]
            self.assertIsInstance(packet, Packet)
            self.assertEqual(packet.get("specification"), "waypoint_clear")
            self.assertEqual(packet.get("to_id"), 2)
            self.assertEqual(to, 2)

            self.assertEqual(self.rf_sensor._queue.qsize(), 0)

    def test_send_tx_frame(self):
        # Providing an invalid packet raises an exception.
        with self.assertRaises(TypeError):
            self.rf_sensor._send_tx_frame(None, to=2)

        # Providing an invalid destination raises an exception.
        with self.assertRaises(TypeError):
            self.rf_sensor._send_tx_frame(Packet())

    def test_receive(self):
        # Verify that the interface requires subclasses to implement
        # the `_receive` method.
        with self.assertRaises(NotImplementedError):
            self.rf_sensor._receive(Packet())

    def test_create_rssi_broadcast_packet(self):
        packet = self.rf_sensor._create_rssi_broadcast_packet()

        self.assertIsInstance(packet, Packet)
        self.assertEqual(packet.get("specification"), "rssi_broadcast")
        self.assertEqual(packet.get("latitude"), 0)
        self.assertEqual(packet.get("longitude"), 0)
        self.assertEqual(packet.get("valid"), True)
        self.assertEqual(packet.get("waypoint_index"), 0)
        self.assertEqual(packet.get("sensor_id"), self.rf_sensor.id)
        self.assertAlmostEqual(packet.get("timestamp"), time.time(), delta=0.1)

    def test_create_rssi_ground_station_packet(self):
        rssi_broadcast_packet = self.rf_sensor._create_rssi_broadcast_packet()
        packet = self.rf_sensor._create_rssi_ground_station_packet(rssi_broadcast_packet)

        self.assertIsInstance(packet, Packet)
        self.assertEqual(packet.get("specification"), "rssi_ground_station")
        self.assertEqual(packet.get("sensor_id"), self.rf_sensor.id)
        self.assertEqual(packet.get("from_latitude"), rssi_broadcast_packet.get("latitude"))
        self.assertEqual(packet.get("from_longitude"), rssi_broadcast_packet.get("longitude"))
        self.assertEqual(packet.get("from_valid"), rssi_broadcast_packet.get("valid"))
        self.assertEqual(packet.get("to_latitude"), 0)
        self.assertEqual(packet.get("to_longitude"), 0)
        self.assertEqual(packet.get("to_valid"), True)
