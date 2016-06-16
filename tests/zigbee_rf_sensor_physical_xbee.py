# Core imports
import thread
import time

# Library imports
import serial
from mock import patch, MagicMock

# Package imports
from ..core.Threadable import Threadable
from ..core.Thread_Manager import Thread_Manager
from ..settings.Arguments import Arguments
from ..zigbee.Packet import Packet
from core_usb_manager import USBManagerTestCase
from settings import SettingsTestCase

class TestZigBeeRFSensorPhysicalXBee(SettingsTestCase, USBManagerTestCase):
    def setUp(self):
        super(TestZigBeeRFSensorPhysicalXBee, self).setUp()

        # We need to mock the XBee module as we do not want to use actual 
        # XBee communication. We assume the XBee module works as expected.
        modules = {
            "xbee": MagicMock(),
            "xbee.ZigBee": MagicMock(),
        }
        self._xbee_patcher = patch.dict("sys.modules", modules)
        self._xbee_patcher.start()

        from ..zigbee.RF_Sensor_Physical_XBee import RF_Sensor_Physical_XBee

        self.arguments = Arguments("settings.json", ["--rf-sensor-id", "1"])
        self.settings = self.arguments.get_settings("rf_sensor_physical_xbee")

        self.thread_manager = Thread_Manager()
        self.location_callback = MagicMock(return_value=((0, 0), 0))
        self.receive_callback = MagicMock()
        self.valid_callback = MagicMock(return_value=True)

        self.usb_manager.index()

        self.rf_sensor = RF_Sensor_Physical_XBee(self.arguments, self.thread_manager,
                                                 self.location_callback,
                                                 self.receive_callback,
                                                 self.valid_callback,
                                                 usb_manager=self.usb_manager)

    def tearDown(self):
        super(TestZigBeeRFSensorPhysicalXBee, self).tearDown()

        self._xbee_patcher.stop()

    def test_initialization(self):
        self.assertEqual(self.rf_sensor._packets, {})
        
        self.assertEqual(self.rf_sensor._sensor, None)
        self.assertEqual(self.rf_sensor._port, self.settings.get("port"))
        self.assertFalse(self.rf_sensor._node_identifier_set)
        self.assertFalse(self.rf_sensor._address_set)
        self.assertEqual(self.rf_sensor._response_delay, self.settings.get("response_delay"))
        self.assertEqual(self.rf_sensor._startup_delay, self.settings.get("startup_delay"))

        sensors = self.settings.get("sensors")
        for index, sensor in enumerate(self.rf_sensor._sensors):
            self.assertEqual(sensor, sensors[index].decode("string_escape"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.rf_sensor.type, "rf_sensor_physical_xbee")

    def test_identity(self):
        # The identity must include the ID, address and network join status.
        self.assertEqual(self.rf_sensor.identity, {
            "id": self.rf_sensor._id,
            "address": self.rf_sensor._format_address(self.rf_sensor._address),
            "joined": self.rf_sensor._joined
        })

    def test_activate(self):
        # Helper function for joining the network.
        def join(*args):
            self.rf_sensor._joined = True

        self.rf_sensor._sensor = MagicMock()
        self.rf_sensor._synchronize = MagicMock()

        with patch.object(self.rf_sensor, "_setup"):
            with patch.object(thread, "start_new_thread"):
                # The sensor must join the network and synchronize its clock.
                with patch.object(time, "sleep", side_effect=join):
                    self.rf_sensor.activate()
                    self.rf_sensor._sensor.send.assert_any_call("at", command="AI")
                    self.rf_sensor._synchronize.assert_called_once_with()

    def test_deactivate(self):
        self.rf_sensor._connection = MagicMock()
        self.rf_sensor._sensor = MagicMock()
        self.rf_sensor._sensor.is_alive = MagicMock(return_value=True)

        self.rf_sensor.deactivate()

        # The sensor must be stopped when it is still active.
        self.rf_sensor._sensor.is_alive.assert_called_once_with()
        self.rf_sensor._sensor.halt.assert_called_once_with()

    def test_discover(self):
        self.rf_sensor._sensor = MagicMock()

        self.rf_sensor.discover(MagicMock())

        # The sensor must send a node discovery packet.
        self.rf_sensor._sensor.send.assert_called_once_with("at", command="ND")

    def test_setup(self):
        self.rf_sensor._set_node_identifier = MagicMock()
        self.rf_sensor._set_address = MagicMock()

        self.rf_sensor._setup()

        # The connection and sensor must be initialized.
        self.assertNotEqual(self.rf_sensor._connection, None)
        self.assertIsInstance(self.rf_sensor._connection, serial.Serial)
        self.assertNotEqual(self.rf_sensor._sensor, None)

        self.rf_sensor._set_node_identifier.assert_called_once_with()
        self.rf_sensor._set_address.assert_called_once_with()

        # When a port is specified, the connection must be initialized too.
        self.rf_sensor._port = self._xbee_port

        self.rf_sensor._setup()

        self.assertNotEqual(self.rf_sensor._connection, None)
        self.assertIsInstance(self.rf_sensor._connection, serial.Serial)

    def test_set_node_identifier(self):
        with patch.object(self.rf_sensor, "_sensor") as sensor_mock:
            with patch.object(time, "sleep", side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    self.rf_sensor._set_node_identifier()

                # The sensor must send a node identification packet.
                sensor_mock.send.assert_called_once_with("at", command="NI")

    def test_set_address(self):
        # Helper function to set the address.
        def set_address(*args):
            self.rf_sensor._address_set = True

        with patch.object(self.rf_sensor, "_sensor") as sensor_mock:
            with patch.object(time, "sleep", side_effect=set_address):
                self.rf_sensor._set_address()

                # The sensor must send two address packets.
                sensor_mock.send.assert_any_call("at", command="SH")
                sensor_mock.send.assert_any_call("at", command="SL")

    def test_error(self):
        with patch.object(Threadable, "interrupt") as interrupt_mock:
            self.rf_sensor._error()

            interrupt_mock.assert_called_once_with()

    def test_loop_body(self):
        self.rf_sensor._send_custom_packets = MagicMock()

        # The sensor must wait until it has joined the network.
        self.rf_sensor._loop_body()
        self.rf_sensor._send_custom_packets.assert_not_called()

        # When the sensor has joined the network, the rest of the
        # loop body must be executed.
        self.rf_sensor._joined = True

        self.rf_sensor._loop_body()
        self.rf_sensor._send_custom_packets.assert_called_once_with()

    def test_send(self):
        # Create two dummy packets, one of them having an associated RSSI value.
        first_packet = self.rf_sensor._create_rssi_broadcast_packet()
        first_packet.set("rssi", 42)
        self.rf_sensor._packets[0] = first_packet

        second_packet = self.rf_sensor._create_rssi_broadcast_packet()
        self.rf_sensor._packets[1] = second_packet

        with patch.object(self.rf_sensor, "_send_tx_frame") as send_tx_frame_mock:
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

            # RSSI ground station packets that have an associated RSSI value must
            # be sent to the ground station. If the RSSI value is missing, then the
            # packet must remain in the packet dictionary. We added two packets
            # to the dictionary at the start of this test, so only the first one
            # may be sent.
            packet, to = calls.pop(0)[0]
            self.assertIsInstance(packet, Packet)
            self.assertEqual(packet.get("specification"), "rssi_broadcast")
            self.assertEqual(packet.get("rssi"), 42)
            self.assertEqual(to, 0)

            self.assertEqual(self.rf_sensor._packets, {
                1: second_packet
            })

    def test_send_tx_frame(self):
        packet = Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 2)

        self.rf_sensor._connection = MagicMock()
        self.rf_sensor._sensor = MagicMock()

        self.rf_sensor._send_tx_frame(packet, to=2)

        to_address = self.rf_sensor._sensors[2]
        self.rf_sensor._sensor.send.assert_called_once_with("tx", dest_addr_long=to_address,
                                                            dest_addr="\xFF\xFE",
                                                            frame_id="\x00",
                                                            data=packet.serialize())

    def test_receive(self):
        # Verify that a packet must be provided.
        with self.assertRaises(TypeError):
            self.rf_sensor._receive()

        # RX packets must be processed.
        self.rf_sensor._process = MagicMock()
        packet = {
            "id": "rx"
        }
        self.rf_sensor._receive(packet)
        self.rf_sensor._process.assert_called_once_with(packet)

        # AT response packets must be processed.
        self.rf_sensor._process_at_response = MagicMock()
        packet = {
            "id": "at_response"
        }
        self.rf_sensor._receive(packet)
        self.rf_sensor._process_at_response.assert_called_once_with(packet)

    def test_process(self):
        packet = Packet()
        packet.set("specification", "rssi_broadcast")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        packet.set("valid", True)
        packet.set("waypoint_index", 1)
        packet.set("sensor_id", 2)
        packet.set("timestamp", time.time())

        self.rf_sensor._process_rssi_broadcast_packet = MagicMock()

        self.rf_sensor._process({
            "rf_data": packet.serialize()
        })

        arguments = self.rf_sensor._process_rssi_broadcast_packet.call_args[0]
        self.assertEqual(arguments[0].get_all(), packet.get_all())

    def test_process_rssi_broadcast_packet(self):
        packet = Packet()
        packet.set("specification", "rssi_broadcast")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        packet.set("valid", True)
        packet.set("waypoint_index", 1)
        packet.set("sensor_id", 2)
        packet.set("timestamp", time.time())

        self.rf_sensor._sensor = MagicMock()

        self.rf_sensor._process_rssi_broadcast_packet(packet)

        self.assertTrue(len(self.rf_sensor._packets), 1)
        frame_id = self.rf_sensor._packets.keys()[0]
        self.rf_sensor._sensor.send.assert_called_once_with("at", command="DB",
                                                            frame_id=frame_id)

    def test_process_at_response(self):
        # AT response DB packets should be processed. The parsed RSSI value
        # should be placed in the original packet in the data object.
        self.rf_sensor._packets = {
            1: self.rf_sensor._create_rssi_broadcast_packet()
        }
        raw_packet = {
            "id": "at_response",
            "frame_id": 1,
            "command": "DB",
            "parameter": "\x4E"
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._packets[1].get("rssi"), -ord("\x4E"))

        # AT response SH packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "SH",
            "parameter": "high"
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._address, "high")

        # If a low part is already present in the address, the high
        # part should be prepended.
        self.rf_sensor._address = "low"
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._address, "highlow")
        self.assertEqual(self.rf_sensor._address_set, True)

        # If the high part is already present in the address (due to
        # a repeated request), it should not be prepended again.
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._address, "highlow")

        self.rf_sensor._address_set = False
        self.rf_sensor._address = None

        # AT response SL packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "SL",
            "parameter": "low"
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._address, "low")

        # If a high part is already present in the address, the low
        # part should be appended.
        self.rf_sensor._address = "high"
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._address, "highlow")
        self.assertEqual(self.rf_sensor._address_set, True)

        # If the low part is already present in the address (due to
        # a repeated request), it should not be appended again.
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._address, "highlow")

        # AT response NI packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "NI",
            "parameter": "4"
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor.id, 4)
        self.assertEqual(self.rf_sensor._scheduler.id, 4)
        self.assertEqual(self.rf_sensor._node_identifier_set, True)

        # AT response AI failure packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "AI",
            "parameter": "\x01"
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._joined, False)

        # AT response AI success packets should be processed.
        raw_packet = {
            "id": "at_response",
            "command": "AI",
            "parameter": "\x00"
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.assertEqual(self.rf_sensor._joined, True)

        # AT response ND packets should be processed.
        self.rf_sensor._discovery_callback = MagicMock()
        raw_packet = {
            "id": "at_response",
            "command": "ND",
            "parameter": {
                "node_identifier": "2",
                "source_addr_long": "\x00\x13\xa2\x00@\xe6n\xbd"
            }
        }
        self.rf_sensor._process_at_response(raw_packet)
        self.rf_sensor._discovery_callback.assert_called_once_with({
            "id": 2,
            "address": "00:13:A2:00:40:E6:6E:BD"
        })

    def test_format_address(self):
        expectations = {
            None: "-",
            "\x00\x13\xa2\x00@\xe6n\xbd": "00:13:A2:00:40:E6:6E:BD"
        }
        for source, target in expectations.iteritems():
            self.assertEqual(self.rf_sensor._format_address(source), target)
