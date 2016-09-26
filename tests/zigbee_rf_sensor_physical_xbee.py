# Core imports
import thread
import time

# Library imports
import serial
from mock import patch, MagicMock, PropertyMock

# Package imports
from ..core.Threadable import Threadable
from ..zigbee.Packet import Packet
from ..zigbee.TDMA_Scheduler import TDMA_Scheduler
from core_usb_manager import USBManagerTestCase
from zigbee_rf_sensor import ZigBeeRFSensorTestCase

class TestZigBeeRFSensorPhysicalXBee(ZigBeeRFSensorTestCase, USBManagerTestCase):
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

        self.settings = self.arguments.get_settings("rf_sensor_physical_xbee")
        self.usb_manager.index()

        self.rf_sensor = self._create_sensor(RF_Sensor_Physical_XBee,
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

        with patch.object(self.rf_sensor, "_sensor") as sensor_mock:
            with patch.object(self.rf_sensor, "_synchronize") as synchronize_mock:
                with patch.object(self.rf_sensor, "_setup"):
                    with patch.object(thread, "start_new_thread"):
                        # The sensor must join the network and synchronize its 
                        # clock via NTP.
                        with patch.object(time, "sleep", side_effect=join):
                            self.rf_sensor.activate()
                            sensor_mock.send.assert_any_call("at", command="AI")
                            synchronize_mock.assert_called_once_with()

    def test_deactivate(self):
        methods = {
            "is_alive.return_value": True
        }
        with patch.object(self.rf_sensor, "_sensor", **methods) as sensor_mock:
            with patch.object(self.rf_sensor, "_connection"):
                self.rf_sensor.deactivate()

                # The sensor must be stopped when it is still active.
                sensor_mock.is_alive.assert_called_once_with()
                sensor_mock.halt.assert_called_once_with()

    def test_start(self):
        # The packet list must be an empty dictionary.
        self.rf_sensor.start()
        self.assertEqual(self.rf_sensor._packets, {})

    def test_discover(self):
        with patch.object(self.rf_sensor, "_sensor") as sensor_mock:
            self.rf_sensor.discover(MagicMock())

            # The sensor must send a node discovery packet.
            sensor_mock.send.assert_called_once_with("at", command="ND")

    def test_setup(self):
        with patch.object(self.rf_sensor, "_set_node_identifier") as set_node_identifier_mock:
            with patch.object(self.rf_sensor, "_set_address") as set_address_mock:
                self.rf_sensor._setup()

                # The connection and sensor must be initialized.
                self.assertNotEqual(self.rf_sensor._connection, None)
                self.assertIsInstance(self.rf_sensor._connection, serial.Serial)
                self.assertNotEqual(self.rf_sensor._sensor, None)

                set_node_identifier_mock.assert_called_once_with()
                set_address_mock.assert_called_once_with()

                # When a port is specified, the connection must be initialized.
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
        with patch.object(self.rf_sensor, "_send_custom_packets") as send_custom_packets_mock:
            # The sensor must wait until it has joined the network.
            self.rf_sensor._loop_body()
            send_custom_packets_mock.assert_not_called()

            # When the sensor has joined the network, the rest of the
            # loop body must be executed.
            self.rf_sensor._joined = True

            self.rf_sensor._loop_body()
            send_custom_packets_mock.assert_called_once_with()

    def test_send(self):
        # Create two dummy packets, one of them having an associated RSSI 
        # value.
        first_packet = self.rf_sensor._create_rssi_broadcast_packet()
        first_packet.set("rssi", 42)
        self.rf_sensor._packets[0] = first_packet

        second_packet = self.rf_sensor._create_rssi_broadcast_packet()
        self.rf_sensor._packets[1] = second_packet

        # If the current time is inside an allocated slot, then packets
        # may be sent.
        with patch.object(self.rf_sensor, "_send_tx_frame") as send_tx_frame_mock:
            in_slot_mock = PropertyMock(return_value=True)
            with patch.object(TDMA_Scheduler, "in_slot", new_callable=in_slot_mock):
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

        # If the current time is not inside an allocated slot, then no
        # packets may be sent.
        with patch.object(self.rf_sensor, "_send_tx_frame") as send_tx_frame_mock:
            in_slot_mock = PropertyMock(return_value=False)
            with patch.object(TDMA_Scheduler, "in_slot", new_callable=in_slot_mock):
                self.rf_sensor._send()
                send_tx_frame_mock.assert_not_called()

    def test_send_tx_frame(self):
        self.packet.set("specification", "waypoint_clear")
        self.packet.set("to_id", 2)

        with patch.object(self.rf_sensor, "_connection"):
            with patch.object(self.rf_sensor, "_sensor") as sensor_mock:
                self.rf_sensor._send_tx_frame(self.packet, to=2)

                to_address = self.rf_sensor._sensors[2]
                sensor_mock.send.assert_called_once_with("tx",
                                                         dest_addr_long=to_address,
                                                         dest_addr="\xFF\xFE",
                                                         frame_id="\x00",
                                                         data=self.packet.serialize())

    def test_receive(self):
        # Verify that a packet must be provided.
        with self.assertRaises(TypeError):
            self.rf_sensor._receive()

        # RX packets must be processed.
        with patch.object(self.rf_sensor, "_process") as process_mock:
            packet = {
                "id": "rx"
            }
            self.rf_sensor._receive(packet)
            process_mock.assert_called_once_with(packet)

        # AT response packets must be processed.
        with patch.object(self.rf_sensor, "_process_at_response") as process_at_response_mock:
            packet = {
                "id": "at_response"
            }
            self.rf_sensor._receive(packet)
            process_at_response_mock.assert_called_once_with(packet)

    def test_process(self):
        self.packet.set("specification", "rssi_broadcast")
        self.packet.set("latitude", 123456789.12)
        self.packet.set("longitude", 123459678.34)
        self.packet.set("valid", True)
        self.packet.set("waypoint_index", 1)
        self.packet.set("sensor_id", 2)
        self.packet.set("timestamp", time.time())

        with patch.object(self.rf_sensor, "_process_rssi_broadcast_packet") as process_rssi_broadcast_packet_mock:
            self.rf_sensor._process({
                "rf_data": self.packet.serialize()
            })

            arguments = process_rssi_broadcast_packet_mock.call_args[0]
            self.assertEqual(arguments[0].get_all(), self.packet.get_all())

    def test_process_rssi_broadcast_packet(self):
        self.packet.set("specification", "rssi_broadcast")
        self.packet.set("latitude", 123456789.12)
        self.packet.set("longitude", 123459678.34)
        self.packet.set("valid", True)
        self.packet.set("waypoint_index", 1)
        self.packet.set("sensor_id", 2)
        self.packet.set("timestamp", time.time())

        with patch.object(self.rf_sensor, "_sensor") as sensor_mock:
            self.rf_sensor._process_rssi_broadcast_packet(self.packet)

            self.assertTrue(len(self.rf_sensor._packets), 1)
            frame_id = self.rf_sensor._packets.keys()[0]
            sensor_mock.send.assert_called_once_with("at", command="DB",
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
        with patch.object(self.rf_sensor, "_discovery_callback") as discovery_callback_mock:
            raw_packet = {
                "id": "at_response",
                "command": "ND",
                "parameter": {
                    "node_identifier": "2",
                    "source_addr_long": "\x00\x13\xa2\x00@\xe6n\xbd"
                }
            }
            self.rf_sensor._process_at_response(raw_packet)
            discovery_callback_mock.assert_called_once_with({
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
