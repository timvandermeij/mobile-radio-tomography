# Core imports
import Queue
import thread
import time

# Library imports
from mock import patch, MagicMock, PropertyMock

# Package imports
from ..core.Thread_Manager import Thread_Manager
from ..core.Threadable import Threadable
from ..settings.Arguments import Arguments
from ..reconstruction.Buffer import Buffer
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import RF_Sensor, DisabledException
from ..zigbee.TDMA_Scheduler import TDMA_Scheduler
from settings import SettingsTestCase
from zigbee_packet import ZigBeePacketTestCase

class ZigBeeRFSensorTestCase(SettingsTestCase, ZigBeePacketTestCase):
    """
    Test case base class that provides the necessities to create one of the
    `RF_Sensor` types of objects.
    """

    def setUp(self):
        super(ZigBeeRFSensorTestCase, self).setUp()

        self.arguments = Arguments("settings.json", ["--rf-sensor-id", "1"])

        self.thread_manager = Thread_Manager()
        self.location_callback = MagicMock(return_value=((0, 0), 0))
        self.receive_callback = MagicMock()
        self.valid_callback = MagicMock(return_value=True)

    def _create_sensor(self, sensor_type, **kwargs):
        """
        Create the RF sensor object. The `sensor_type` is a class that is either
        `RF_Sensor` or a subclass thereof. Additional keyword arguments are
        passed through to the object initialization.

        The resulting `RF_Sensor` object is returned.
        """

        return sensor_type(self.arguments, self.thread_manager,
                           self.location_callback, self.receive_callback,
                           self.valid_callback, **kwargs)

class TestZigBeeRFSensor(ZigBeeRFSensorTestCase):
    def setUp(self):
        super(TestZigBeeRFSensor, self).setUp()

        self.settings = self.arguments.get_settings("zigbee_base")

        type_mock = PropertyMock(return_value="zigbee_base")
        with patch.object(RF_Sensor, "type", new_callable=type_mock):
            self.rf_sensor = self._create_sensor(RF_Sensor)

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
        self.assertEqual(self.rf_sensor._packets, [])
        self.assertIsInstance(self.rf_sensor._queue, Queue.Queue)
        self.assertEqual(self.rf_sensor._queue.qsize(), 0)

        self.assertEqual(self.rf_sensor._joined, False)
        self.assertEqual(self.rf_sensor._activated, False)
        self.assertEqual(self.rf_sensor._started, False)

        self.assertEqual(self.rf_sensor._loop_delay, self.settings.get("loop_delay"))

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

    def test_activate(self):
        with patch.object(RF_Sensor, "_setup") as setup_mock:
            with patch.object(thread, "start_new_thread") as start_new_thread_mock:
                self.rf_sensor.activate()

                # The sensor must be setup and the loop thread must be started.
                self.assertTrue(self.rf_sensor._activated)
                self.assertEqual(setup_mock.call_count, 1)
                self.assertEqual(start_new_thread_mock.call_count, 1)

    def test_deactivate(self):
        connection_mock = MagicMock()

        with patch.object(RF_Sensor, "_setup"):
            with patch.object(thread, "start_new_thread"):
                self.rf_sensor.activate()
                self.rf_sensor._connection = connection_mock
                self.rf_sensor.deactivate()

                # The connection must be closed and the sensor must be deactivated.
                self.assertEqual(self.rf_sensor._activated, False)
                self.assertEqual(connection_mock.close.call_count, 1)
                self.assertEqual(self.rf_sensor._connection, None)

    def test_start(self):
        # The sensor must be started for sending RSSI broadcast/ground
        # station packets. Make sure that the schedule will try to shift again 
        # when the measurements start.
        self.rf_sensor.start()
        self.assertTrue(self.rf_sensor._started)
        self.assertEqual(self.rf_sensor._packets, [])
        self.assertNotEqual(self.rf_sensor._scheduler.timestamp, 0.0)

    def test_stop(self):
        # Pertent we start the RF sensor so that we know that `stop` functions.
        self.rf_sensor.start()

        # The sensor must be stopped for sending custom packets. Make sure that 
        # the scheduler timestamp is reset, so that it updates correctly in 
        # case we restart the sensor measurements.
        self.rf_sensor.stop()
        self.assertEqual(self.rf_sensor._started, False)
        self.assertEqual(self.rf_sensor._scheduler.timestamp, 0.0)

    def test_enqueue(self):
        # Providing a packet that is not a `Packet` object raises an exception.
        with self.assertRaises(TypeError):
            self.rf_sensor.enqueue({
                "foo": "bar"
            })

        # Providing a private packet raises an exception.
        with self.assertRaises(ValueError):
            self.packet.set("specification", "rssi_broadcast")
            self.rf_sensor.enqueue(self.packet)

        # Packets that do not have a destination must be broadcasted.
        # We subtract one because we do not send to ourself.
        self.packet.set("specification", "waypoint_clear")
        self.packet.set("to_id", 2)
        self.rf_sensor.enqueue(self.packet)

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
        self.rf_sensor.enqueue(self.packet, to=2)

        self.assertEqual(self.rf_sensor._queue.qsize(), 1)
        self.assertEqual(self.rf_sensor._queue.get(), {
            "packet": self.packet,
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
        self.rf_sensor._activated = True

        with patch.object(Threadable, "interrupt") as interrupt_mock:
            with patch.object(RF_Sensor, "_loop_body") as loop_body_mock:
                # The loop body and interrupt handler must be called when
                # an exception other than a `DisabledException` is raised.
                loop_body_mock.configure_mock(side_effect=RuntimeError)
                self.rf_sensor._loop()
                loop_body_mock.assert_called_once_with()
                interrupt_mock.assert_called_once_with()

        with patch.object(Threadable, "interrupt") as interrupt_mock:
            with patch.object(RF_Sensor, "_loop_body") as loop_body_mock:
                # The loop body must be called when a `DisabledException` is
                # raised, but nothing else must happen.
                loop_body_mock.configure_mock(side_effect=DisabledException)
                self.rf_sensor._loop()
                loop_body_mock.assert_called_once_with()
                interrupt_mock.assert_not_called()

    def test_loop_body(self):
        with patch.object(RF_Sensor, "_send_custom_packets") as send_custom_packets_mock:
            # Send custom packets when the sensor has been activated,
            # but not started.
            self.rf_sensor._loop_body()
            send_custom_packets_mock.assert_called_once_with()

        with patch.object(TDMA_Scheduler, "update") as update_mock:
            with patch.object(RF_Sensor, "_send") as send_mock:
                self.rf_sensor._started = True

                # Send RSSI broadcast/ground station packets when the sensor
                # has been activated and started.
                self.rf_sensor._loop_body()

                update_mock.assert_called_once_with()
                send_mock.assert_called_once_with()

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
        self.packet.set("specification", "waypoint_clear")
        self.packet.set("to_id", 2)
        self.rf_sensor.enqueue(self.packet, to=2)

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
        # Having a closed connection raises an exception.
        with self.assertRaises(DisabledException):
            self.rf_sensor._send_tx_frame(self.packet, to=2)

        with patch.object(self.rf_sensor, "_connection"):
            # Providing an invalid packet raises an exception.
            with self.assertRaises(TypeError):
                self.rf_sensor._send_tx_frame(None, to=2)

            # Providing an invalid destination raises an exception.
            with self.assertRaises(TypeError):
                self.rf_sensor._send_tx_frame(self.packet)

    def test_receive(self):
        # Verify that the interface requires subclasses to implement
        # the `_receive` method.
        with self.assertRaises(NotImplementedError):
            self.rf_sensor._receive(packet=self.packet)

    def test_create_rssi_broadcast_packet(self):
        packet = self.rf_sensor._create_rssi_broadcast_packet()

        self.assertIsInstance(packet, Packet)
        self.assertEqual(packet.get("specification"), "rssi_broadcast")
        self.assertEqual(packet.get("latitude"), 0)
        self.assertEqual(packet.get("longitude"), 0)
        self.assertTrue(packet.get("valid"))
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
        self.assertTrue(packet.get("to_valid"))
