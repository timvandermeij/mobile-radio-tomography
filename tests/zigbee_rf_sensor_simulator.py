# Core imports
import socket

# Library imports
from mock import patch, MagicMock

# Package imports
from ..core.Thread_Manager import Thread_Manager
from ..reconstruction.Buffer import Buffer
from ..settings.Arguments import Arguments
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import DisabledException
from ..zigbee.RF_Sensor_Simulator import RF_Sensor_Simulator
from settings import SettingsTestCase

class TestZigBeeRFSensorSimulator(SettingsTestCase):
    def setUp(self):
        super(TestZigBeeRFSensorSimulator, self).setUp()

        self.arguments = Arguments("settings.json", ["--rf-sensor-id", "1"])
        self.settings = self.arguments.get_settings("rf_sensor_simulator")

        self.thread_manager = Thread_Manager()
        self.location_callback = MagicMock(return_value=((0, 0), 0))
        self.receive_callback = MagicMock()
        self.valid_callback = MagicMock(return_value=True)

        self.rf_sensor = RF_Sensor_Simulator(self.arguments, self.thread_manager,
                                             self.location_callback,
                                             self.receive_callback,
                                             self.valid_callback)

    def test_initialization(self):
        # The simulated sensor must have joined the network immediately.
        self.assertTrue(self.rf_sensor._joined)

        # The simulated sensor must have its networking information set.
        self.assertEqual(self.rf_sensor._ip, self.settings.get("socket_ip"))
        self.assertEqual(self.rf_sensor._port, self.settings.get("socket_port"))
        address = "{}:{}".format(self.rf_sensor._ip, 
                                 self.rf_sensor._port + self.rf_sensor._id)
        self.assertEqual(self.rf_sensor._address, address)

        # The buffer size must be set.
        self.assertEqual(self.rf_sensor._buffer_size, self.settings.get("buffer_size"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.rf_sensor.type, "rf_sensor_simulator")

    def test_discover(self):
        callback_mock = MagicMock()
        self.rf_sensor.discover(callback_mock)

        calls = callback_mock.call_args_list

        # Each vehicle must report the identity of its RF sensor.
        for vehicle_id in xrange(1, self.rf_sensor.number_of_sensors + 1):
            response = calls.pop(0)[0][0]
            self.assertEqual(response, {
                "id": vehicle_id,
                "address": "{}:{}".format(self.rf_sensor._ip,
                                          self.rf_sensor._port + vehicle_id)
            })

    def test_setup(self):
        # The socket connection must be opened.
        self.rf_sensor._setup()

        self.assertIsInstance(self.rf_sensor._connection, socket.socket)

    def test_loop_body(self):
        self.rf_sensor._receive = MagicMock()
        self.rf_sensor._connection = MagicMock()
        self.rf_sensor._connection.recv = MagicMock()
        recv_mock = self.rf_sensor._connection.recv

        with patch.object(RF_Sensor_Simulator, "_send"):
            # The socket's receive method must be called, but when a socket
            # error occurs (i.e., when there is no data available), we ignore
            # the error and continue.
            recv_mock.configure_mock(side_effect=socket.error)
            self.rf_sensor._loop_body()
            recv_mock.assert_called_once_with(self.settings.get("buffer_size"))
            recv_mock.reset_mock()

            # The socket's receive method must be called, but when an
            # attribute error occurs (i.e., when the sensor has been
            # deactivated), a `DisabledException` must be raised.
            recv_mock.configure_mock(side_effect=AttributeError)
            with self.assertRaises(DisabledException):
                self.rf_sensor._loop_body()

            recv_mock.assert_called_once_with(self.settings.get("buffer_size"))
            recv_mock.reset_mock()

            # Correct serialized packets must be received.
            packet = "\x06H\xe1zT4o\x9dA\xf6(\\E\xa5q\x9dA\xcd\xcc\xcc\xcc\xcc\xcc\x10@\x03\x16\x00\x00\x00\x02"
            recv_mock.configure_mock(side_effect=None, return_value=packet)

            self.rf_sensor._loop_body()

            recv_mock.assert_called_once_with(self.settings.get("buffer_size"))
            self.assertEqual(self.rf_sensor._receive.call_count, 1)
            self.assertEqual(self.rf_sensor._receive.call_args[0][0].get_all(), {
                "specification": "waypoint_add",
                "latitude": 123456789.12,
                "longitude": 123496785.34,
                "altitude": 4.2,
                "wait_id": 3,
                "index": 22,
                "to_id": 2
            })

    def test_send_tx_frame(self):
        connection_mock = MagicMock()

        packet = Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 2)

        self.rf_sensor._connection = connection_mock
        self.rf_sensor._send_tx_frame(packet, to=2)

        # The packet must be sent over the socket connection.
        address = (self.rf_sensor._ip, self.rf_sensor._port + 2)
        connection_mock.sendto.assert_called_once_with(packet.serialize(), address)

    def test_receive(self):
        scheduler_next_timestamp = self.rf_sensor._scheduler_next_timestamp

        packet = self.rf_sensor._create_rssi_broadcast_packet()
        self.rf_sensor._receive(packet)

        # The receive callback must be called with the packet.
        self.receive_callback.assert_called_once_with(packet)

        # The scheduler's next timestamp must be updated.
        self.assertNotEqual(scheduler_next_timestamp,
                            self.rf_sensor._scheduler_next_timestamp)

        # A ground station packet must be put in the packet list.
        self.assertEqual(len(self.rf_sensor._packets), 1)
        self.assertEqual(self.rf_sensor._packets[0].get("specification"),
                         "rssi_ground_station")
        self.assertIsInstance(self.rf_sensor._packets[0].get("rssi"), int)

        # If the sensor is the ground station, the packet must be put
        # into the buffer if it is available.
        self.rf_sensor.buffer = MagicMock(spec=Buffer)
        self.rf_sensor._id = 0
        self.rf_sensor._receive(packet)

        self.rf_sensor.buffer.put.assert_called_once_with(packet)
