# Core imports
import struct
import thread
import time

# Library imports
from mock import call, patch, MagicMock

# Package imports
from ..core.Thread_Manager import Thread_Manager
from ..core.WiringPi import WiringPi
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import DisabledException
from ..zigbee.RF_Sensor_Physical_Texas_Instruments import RF_Sensor_Physical_Texas_Instruments
from ..zigbee.RF_Sensor_Physical_Texas_Instruments import CC2530_Packet, Raspberry_Pi_GPIO_Pin_Mode
from ..zigbee.TDMA_Scheduler import TDMA_Scheduler
from core_wiringpi import WiringPiTestCase
from core_usb_manager import USBManagerTestCase
from zigbee_rf_sensor import ZigBeeRFSensorTestCase

class TestZigBeeRFSensorPhysicalTexasInstruments(ZigBeeRFSensorTestCase, USBManagerTestCase, WiringPiTestCase):
    def setUp(self):
        super(TestZigBeeRFSensorPhysicalTexasInstruments, self).setUp()

        self.settings = self.arguments.get_settings("rf_sensor_physical_texas_instruments")
        self.usb_manager.index()

        self.rf_sensor = self._create_sensor(RF_Sensor_Physical_Texas_Instruments,
                                             usb_manager=self.usb_manager)

    def test_initialization(self):
        self.assertEqual(self.rf_sensor._address, str(self.rf_sensor.id))
        self.assertTrue(self.rf_sensor._joined)
        self.assertEqual(self.rf_sensor._polling_time, 0.0)

        self.assertEqual(self.rf_sensor._packet_length, self.settings.get("packet_length"))
        self.assertEqual(self.rf_sensor._polling_delay, self.settings.get("polling_delay"))
        self.assertEqual(self.rf_sensor._reset_delay, self.settings.get("reset_delay"))
        self.assertEqual(self.rf_sensor._shift_minimum, self.settings.get("shift_minimum"))
        self.assertEqual(self.rf_sensor._shift_maximum, self.settings.get("shift_maximum"))

        self.assertEqual(self.rf_sensor._pins["rx_pin"], self.settings.get("rx_pin"))
        self.assertEqual(self.rf_sensor._pins["tx_pin"], self.settings.get("tx_pin"))
        self.assertEqual(self.rf_sensor._pins["rts_pin"], self.settings.get("rts_pin"))
        self.assertEqual(self.rf_sensor._pins["cts_pin"], self.settings.get("cts_pin"))
        self.assertEqual(self.rf_sensor._pins["reset_pin"], self.settings.get("reset_pin"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.rf_sensor.type, "rf_sensor_physical_texas_instruments")

    @patch.object(RF_Sensor_Physical_Texas_Instruments, "_synchronize")
    def test_activate(self, synchronize_mock):
        with patch.object(RF_Sensor_Physical_Texas_Instruments, "_setup"):
            with patch.object(thread, "start_new_thread"):
                self.rf_sensor.activate()
                synchronize_mock.assert_called_once_with()

    def test_start(self):
        self.rf_sensor.start()
        self.assertNotEqual(self.rf_sensor._polling_time, 0.0)

    @patch.object(RF_Sensor_Physical_Texas_Instruments, "_send_tx_frame")
    def test_discover(self, send_tx_frame_mock):
        self.rf_sensor.discover(MagicMock())

        calls = send_tx_frame_mock.call_args_list

        # Ping/pong packets must be sent to all sensors in the network.
        for to_id in xrange(1, self.rf_sensor.number_of_sensors + 1):
            packet, to = calls.pop(0)[0]
            self.assertIsInstance(packet, Packet)
            self.assertEqual(packet.get("specification"), "ping_pong")
            self.assertEqual(packet.get("sensor_id"), to_id)
            self.assertEqual(to, to_id)

    @patch.object(time, "sleep")
    def test_setup(self, sleep_mock):
        connection_mock = MagicMock()
        methods = {
            "get_cc2530_device.return_value": connection_mock,
            "get_cc2531_device.return_value": connection_mock
        }
        with patch.object(self.rf_sensor, "_usb_manager", **methods) as usb_manager_mock:
            # The ground station must be a CC2531 device and its connection 
            # must be established and configured.
            self.rf_sensor._id = 0
            self.rf_sensor._setup()
            usb_manager_mock.get_cc2531_device.assert_called_once_with()
            self.assertEqual(self.rf_sensor._connection, connection_mock)

            configuration_packet = struct.pack("<BB", CC2530_Packet.CONFIGURATION, self.rf_sensor.id)
            connection_mock.write.assert_called_once_with(configuration_packet)

            # Other RF sensors must be connected to a Raspberry Pi device.
            self.rf_sensor._id = 1
            with self.assertRaises(RuntimeError):
                self.rf_sensor._setup()

            # Other RF sensors must be CC2530 devices and they must be 
            # configured.
            connection_mock.reset_mock()
            usb_manager_mock.reset_mock()

            with patch.object(WiringPi, "is_raspberry_pi", return_value=True):
                with patch.object(WiringPi, "module") as wiringpi_mock:
                    self.rf_sensor._setup()

                    wiringpi_mock.pinModeAlt.assert_has_calls([
                        call(self.settings.get("rx_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT0),
                        call(self.settings.get("tx_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT0),
                        call(self.settings.get("rts_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT3),
                        call(self.settings.get("cts_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT3)
                    ])

                    usb_manager_mock.get_cc2530_device.assert_called_once_with()
                    self.assertEqual(self.rf_sensor._connection, connection_mock)

                    reset_pin = self.settings.get("reset_pin")
                    wiringpi_mock.pinMode.assert_called_once_with(reset_pin,
                                                                  wiringpi_mock.OUTPUT)
                    wiringpi_mock.digitalWrite.assert_any_call(reset_pin, 0)
                    sleep_mock.assert_any_call(self.settings.get("reset_delay"))
                    wiringpi_mock.digitalWrite.assert_any_call(reset_pin, 1)
                    self.assertEqual(wiringpi_mock.digitalWrite.call_count, 2)

                    connection_mock.reset_input_buffer.assert_called_once_with()

    def test_loop_body(self):
        # Shifting the schedule must be handled.
        self.rf_sensor._started = True

        with patch.object(TDMA_Scheduler, "shift") as shift_mock:
            with patch.object(TDMA_Scheduler, "update") as update_mock:
                with patch.object(RF_Sensor_Physical_Texas_Instruments, "_receive") as receive_mock:
                    try:
                        self.rf_sensor._loop_body()
                    except DisabledException:
                        pass

                    receive_mock.assert_called_once_with()
                    self.assertEqual(shift_mock.call_count, 1)
                    self.assertEqual(update_mock.call_count, 1)
                    self.assertNotEqual(self.rf_sensor._polling_time, 0.0)

        # Regular updates must be handled.
        self.rf_sensor._started = False

        with patch.object(RF_Sensor_Physical_Texas_Instruments, "_receive") as receive_mock:
            # The receive method must be called.
            self.rf_sensor._loop_body()

            receive_mock.assert_called_once_with()

    def test_send_tx_frame(self):
        self.packet.set("specification", "waypoint_clear")
        self.packet.set("to_id", 2)

        with patch.object(self.rf_sensor, "_connection") as connection_mock:
            self.rf_sensor._send_tx_frame(self.packet, to=2)

            # The packet must be sent over the serial connection. The packet is 
            # serialized using the struct format "BBB80s", i.e., three 
            # characters and a string padded to 80 (packet length setting) 
            # bytes. We add the padding manually here.
            serialized_packet = "\x02\x02\x02\x05\x02{}".format("\x00" * 78)
            connection_mock.write.assert_called_once_with(serialized_packet)
            connection_mock.flush.assert_called_once_with()

    @patch.object(RF_Sensor_Physical_Texas_Instruments, "_process")
    def test_receive(self, process_mock):
        with patch.object(self.rf_sensor, "_connection") as connection_mock:
            # Nothing should be done when there is not enough data in the 
            # serial buffer.
            connection_mock.in_waiting = 0
            self.rf_sensor._receive()
            connection_mock.read.assert_not_called()

            # Create the `Packet` object for processing if there is enough data 
            # in the serial buffer.
            serialized_packet = "\x02\x05\x02{}\x2A".format("\x00" * 78)
            connection_mock.in_waiting = len(serialized_packet)
            connection_mock.read.configure_mock(return_value=serialized_packet)

            self.rf_sensor._receive()

            self.assertNotEqual(self.rf_sensor._polling_time, 0.0)

            arguments = process_mock.call_args[0]
            keyword_arguments = process_mock.call_args[1]
            self.assertIsInstance(arguments[0], Packet)
            self.assertEqual(arguments[0].get_all(), {
                "specification": "waypoint_clear",
                "to_id": 2
            })
            self.assertEqual(keyword_arguments["rssi"], 42)

            # Any errors must be logged, but must not crash the process.
            connection_mock.in_waiting = len(serialized_packet)
            connection_mock.read.configure_mock(return_value=serialized_packet)

            with patch.object(self.rf_sensor, "_process", side_effect=ValueError):
                with patch.object(Thread_Manager, "log") as log_mock:
                    self.rf_sensor._receive()

                    log_mock.assert_called_once_with(self.rf_sensor.type)

    @patch.object(RF_Sensor_Physical_Texas_Instruments, "_process_rssi_broadcast_packet")
    def test_process(self, process_rssi_broadcast_packet_mock):
        # RSSI value must be provided.
        with self.assertRaises(TypeError):
            self.rf_sensor._process(Packet())

        # Ping/pong packets must be handled on the ground station.
        with patch.object(self.rf_sensor, "_discovery_callback") as discovery_callback_mock:
            self.rf_sensor._id = 0

            packet = Packet()
            packet.set("specification", "ping_pong")
            packet.set("sensor_id", 2)

            self.rf_sensor._process(packet, rssi=42)
            discovery_callback_mock.assert_called_once_with({
                "id": packet.get("sensor_id"),
                "address": str(packet.get("sensor_id"))
            })
            process_rssi_broadcast_packet_mock.assert_not_called()

        # Other RF sensors must respond to ping/pong packets.
        with patch.object(self.rf_sensor, "_send_tx_frame") as send_tx_frame_mock:
            self.rf_sensor._id = 1

            packet = Packet()
            packet.set("specification", "ping_pong")

            self.rf_sensor._process(packet, rssi=42)
            send_tx_frame_mock.assert_called_once_with(packet, 0)
            process_rssi_broadcast_packet_mock.assert_not_called()

        # Other RF sensors must handle RSSI broadcast packets.
        packet = Packet()
        packet.set("specification", "rssi_broadcast")

        self.rf_sensor._process(packet, rssi=42)
        process_rssi_broadcast_packet_mock.assert_called_once_with(packet,
                                                                   rssi=42)

    def test_process_rssi_broadcast_packet(self):
        # RSSI value must be provided.
        with self.assertRaises(TypeError):
            self.rf_sensor._process_rssi_broadcast_packet(Packet())

        packet = self.rf_sensor._create_rssi_broadcast_packet()

        self.rf_sensor._process_rssi_broadcast_packet(packet, rssi=42)

        # A ground station packet must be put in the packet list.
        self.assertEqual(len(self.rf_sensor._packets), 1)
        self.assertEqual(self.rf_sensor._packets[0].get("specification"),
                         "rssi_ground_station")
        self.assertEqual(self.rf_sensor._packets[0].get("rssi"), 42)
