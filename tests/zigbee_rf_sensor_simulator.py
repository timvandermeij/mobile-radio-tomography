# Core imports
import socket

# Library imports
from mock import patch, MagicMock

# Package imports
from ..reconstruction.Buffer import Buffer
from ..zigbee.RF_Sensor import DisabledException
from ..zigbee.RF_Sensor_Simulator import RF_Sensor_Simulator
from zigbee_rf_sensor import ZigBeeRFSensorTestCase

class TestZigBeeRFSensorSimulator(ZigBeeRFSensorTestCase):
    def setUp(self):
        super(TestZigBeeRFSensorSimulator, self).setUp()

        self.settings = self.arguments.get_settings("rf_sensor_simulator")
        self.rf_sensor = self._create_sensor(RF_Sensor_Simulator)

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

    @patch.object(RF_Sensor_Simulator, "_receive")
    @patch.object(RF_Sensor_Simulator, "_send")
    def test_loop_body(self, send_mock, receive_mock):
        with patch.object(self.rf_sensor, "_connection") as connection_mock:
            recv_mock = connection_mock.recv

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
            recv_mock.configure_mock(side_effect=None,
                                     return_value=self.waypoint_add_message)

            self.rf_sensor._loop_body()

            recv_mock.assert_called_once_with(self.settings.get("buffer_size"))
            self.assertEqual(receive_mock.call_count, 1)
            kwargs = receive_mock.call_args[1]
            self.assertEqual(kwargs["packet"].get_all(),
                             self.waypoint_add_packet.get_all())

    def test_send_tx_frame(self):
        self.packet.set("specification", "waypoint_clear")
        self.packet.set("to_id", 2)

        with patch.object(self.rf_sensor, "_connection") as connection_mock:
            self.rf_sensor._send_tx_frame(self.packet, to=2)

            # The packet must be sent over the socket connection.
            address = (self.rf_sensor._ip, self.rf_sensor._port + 2)
            connection_mock.sendto.assert_called_once_with(self.packet.serialize(),
                                                           address)

    def test_receive(self):
        self.rf_sensor.start()

        # Not providing a packet raises an exception.
        with self.assertRaises(TypeError):
            self.rf_sensor._receive()

        timestamp = self.rf_sensor._scheduler.timestamp

        packet = self.rf_sensor._create_rssi_broadcast_packet()
        self.rf_sensor._receive(packet=packet)

        # The receive callback must be called with the packet.
        self.receive_callback.assert_called_once_with(packet)

        # The scheduler's timestamp must be updated.
        self.assertNotEqual(timestamp, self.rf_sensor._scheduler.timestamp)

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
