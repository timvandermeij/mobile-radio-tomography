# Core imports
import struct
import thread
import time

# Library imports
from mock import call, patch, MagicMock

# Package imports
from ..core.Thread_Manager import Thread_Manager
from ..core.WiringPi import WiringPi
from ..settings.Arguments import Arguments
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import DisabledException
from ..zigbee.RF_Sensor_Physical_Texas_Instruments import RF_Sensor_Physical_Texas_Instruments
from ..zigbee.RF_Sensor_Physical_Texas_Instruments import CC2530_Packet, Raspberry_Pi_GPIO_Pin_Mode
from ..zigbee.TDMA_Scheduler import TDMA_Scheduler
from core_usb_manager import USBManagerTestCase
from settings import SettingsTestCase

class TestZigBeeRFSensorPhysicalTexasInstruments(SettingsTestCase, USBManagerTestCase):
    def setUp(self):
        super(TestZigBeeRFSensorPhysicalTexasInstruments, self).setUp()

        self.arguments = Arguments("settings.json", ["--rf-sensor-id", "1"])
        self.settings = self.arguments.get_settings("rf_sensor_physical_texas_instruments")

        self.thread_manager = Thread_Manager()
        self.location_callback = MagicMock(return_value=((0, 0), 0))
        self.receive_callback = MagicMock()
        self.valid_callback = MagicMock(return_value=True)

        self.usb_manager.index()

        self.rf_sensor = RF_Sensor_Physical_Texas_Instruments(self.arguments,
                                                              self.thread_manager,
                                                              self.location_callback,
                                                              self.receive_callback,
                                                              self.valid_callback,
                                                              usb_manager=self.usb_manager)

    def test_initialization(self):
        self.assertEqual(self.rf_sensor._address, str(self.rf_sensor.id))
        self.assertTrue(self.rf_sensor._joined)
        self.assertFalse(self.rf_sensor._other_packet_received)

        self.assertEqual(self.rf_sensor._packet_length, self.settings.get("packet_length"))
        self.assertEqual(self.rf_sensor._reset_delay, self.settings.get("reset_delay"))

        self.assertEqual(self.rf_sensor._pins["rx_pin"], self.settings.get("rx_pin"))
        self.assertEqual(self.rf_sensor._pins["tx_pin"], self.settings.get("tx_pin"))
        self.assertEqual(self.rf_sensor._pins["rts_pin"], self.settings.get("rts_pin"))
        self.assertEqual(self.rf_sensor._pins["cts_pin"], self.settings.get("cts_pin"))
        self.assertEqual(self.rf_sensor._pins["reset_pin"], self.settings.get("reset_pin"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.rf_sensor.type, "rf_sensor_physical_texas_instruments")

    def test_activate(self):
        self.rf_sensor._synchronize = MagicMock()

        with patch.object(RF_Sensor_Physical_Texas_Instruments, "_setup"):
            with patch.object(thread, "start_new_thread"):
                self.rf_sensor.activate()
                self.rf_sensor._synchronize.assert_called_once_with()

    def test_discover(self):
        with patch.object(RF_Sensor_Physical_Texas_Instruments, "_send_tx_frame") as send_tx_frame_mock:
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
        usb_manager_mock = MagicMock(return_value=connection_mock)

        # The ground station must be a CC2531 device and it must be configured.
        self.rf_sensor._id = 0
        self.rf_sensor._usb_manager.get_cc2531_device = usb_manager_mock
        self.rf_sensor._setup()
        self.rf_sensor._usb_manager.get_cc2531_device.assert_called_once_with()
        self.assertEqual(self.rf_sensor._connection, connection_mock)

        configuration_packet = struct.pack("<BB", CC2530_Packet.CONFIGURATION, self.rf_sensor.id)
        connection_mock.write.assert_called_once_with(configuration_packet)

        # Other RF sensors must be connected to a Raspberry Pi device.
        self.rf_sensor._id = 1
        with self.assertRaises(RuntimeError):
            self.rf_sensor._setup()

        # Other RF sensors must be CC2530 devices and they must be configured.
        connection_mock.reset_mock()
        usb_manager_mock.reset_mock()

        with patch.object(WiringPi, "is_raspberry_pi", return_value=True):
            with patch.object(WiringPi, "module") as wiringpi_mock:
                self.rf_sensor._usb_manager.get_cc2530_device = usb_manager_mock

                self.rf_sensor._setup()

                wiringpi_mock.pinModeAlt.assert_has_calls([
                    call(self.settings.get("rx_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT0),
                    call(self.settings.get("tx_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT0),
                    call(self.settings.get("rts_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT3),
                    call(self.settings.get("cts_pin"), Raspberry_Pi_GPIO_Pin_Mode.ALT3)
                ])

                self.rf_sensor._usb_manager.get_cc2530_device.assert_called_once_with()
                self.assertEqual(self.rf_sensor._connection, connection_mock)

                wiringpi_mock.pinMode.assert_called_once_with(self.settings.get("reset_pin"),
                                                              wiringpi_mock.OUTPUT)
                wiringpi_mock.digitalWrite.assert_any_call(self.settings.get("reset_pin"), 0)
                sleep_mock.assert_called_once_with(self.settings.get("reset_delay"))
                wiringpi_mock.digitalWrite.assert_any_call(self.settings.get("reset_pin"), 1)
                self.assertEqual(wiringpi_mock.digitalWrite.call_count, 2)

                connection_mock.reset_input_buffer.assert_called_once_with()

    def test_loop_body(self):
        self.rf_sensor._started = True

        with patch.object(TDMA_Scheduler, "shift") as shift_mock:
            with patch.object(RF_Sensor_Physical_Texas_Instruments, "_receive") as receive_mock:
                # The receive method must be called, as well as the scheduler's
                # shift method.
                try:
                    self.rf_sensor._loop_body()
                except DisabledException:
                    pass

                receive_mock.assert_called_once_with()
                self.assertEqual(shift_mock.call_count, 1)

    def test_send_tx_frame(self):
        packet = Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 2)

        self.rf_sensor._connection = MagicMock()

        self.rf_sensor._send_tx_frame(packet, to=2)

        # The packet must be sent over the serial connection. The packet is serialized
        # using the struct format "BBB80s", i.e., three characters and a string padded
        # to 80 (packet length setting) bytes. We add the padding manually here.
        serialized_packet = "\x02\x02\x02\x05\x02{}".format("\x00" * 78)
        self.rf_sensor._connection.write.assert_called_once_with(serialized_packet)
        self.rf_sensor._connection.flush.assert_called_once_with()

    def test_receive(self):
        # Nothing should be done when there is not enough data in the serial buffer.
        self.rf_sensor._connection = MagicMock()
        self.rf_sensor._connection.in_waiting = 0
        self.rf_sensor._receive()
        self.rf_sensor._connection.read.assert_not_called()

        # Create the `Packet` object if there is enough data in the serial buffer.
        serialized_packet = "\x02\x05\x02{}\x2A".format("\x00" * 78)
        self.rf_sensor._connection.in_waiting = len(serialized_packet)
        self.rf_sensor._connection.read.configure_mock(return_value=serialized_packet)
        self.rf_sensor._process = MagicMock()

        self.rf_sensor._receive()

        self.assertTrue(self.rf_sensor._other_packet_received)

        arguments = self.rf_sensor._process.call_args[0]
        keyword_arguments = self.rf_sensor._process.call_args[1]
        self.assertIsInstance(arguments[0], Packet)
        self.assertEqual(arguments[0].get_all(), {
            "specification": "waypoint_clear",
            "to_id": 2
        })
        self.assertEqual(keyword_arguments["rssi"], 42)

    def test_process(self):
        # RSSI value must be provided.
        with self.assertRaises(TypeError):
            self.rf_sensor._process(Packet())

        self.rf_sensor._process_rssi_broadcast_packet = MagicMock()

        # Ping/pong packets must be handled on the ground station.
        self.rf_sensor._discovery_callback = MagicMock()
        self.rf_sensor._id = 0

        packet = Packet()
        packet.set("specification", "ping_pong")
        packet.set("sensor_id", 2)

        self.rf_sensor._process(packet, rssi=42)
        self.rf_sensor._discovery_callback.assert_called_once_with({
            "id": packet.get("sensor_id"),
            "address": str(packet.get("sensor_id"))
        })
        self.rf_sensor._process_rssi_broadcast_packet.assert_not_called()

        # Other RF sensors must respond to ping/pong packets.
        self.rf_sensor._send_tx_frame = MagicMock()
        self.rf_sensor._id = 1

        packet = Packet()
        packet.set("specification", "ping_pong")

        self.rf_sensor._process(packet, rssi=42)
        self.rf_sensor._send_tx_frame.assert_called_once_with(packet, 0)
        self.rf_sensor._process_rssi_broadcast_packet.assert_not_called()

        # Other RF sensors must handle RSSI broadcast packets.
        packet = Packet()
        packet.set("specification", "rssi_broadcast")

        self.rf_sensor._process(packet, rssi=42)
        self.rf_sensor._process_rssi_broadcast_packet.assert_called_once_with(packet, rssi=42)

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
