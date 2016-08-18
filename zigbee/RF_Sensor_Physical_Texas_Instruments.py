# Core imports
import random
import struct
import time

# Package imports
from ..core.WiringPi import WiringPi
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor_Physical import RF_Sensor_Physical

class Raspberry_Pi_GPIO_Pin_Mode(object):
    """
    Alternative pin modes for the Raspberry Pi GPIO pins for use with WiringPi.

    Refer to https://github.com/WiringPi/WiringPi/blob/master/wiringPi/wiringPi.c#L118
    for the source of these mode selection bits.
    """

    ALT0 = 0b100
    ALT1 = 0b101
    ALT2 = 0b110
    ALT3 = 0b111
    ALT4 = 0b011
    ALT5 = 0b010

class CC2530_Packet(object):
    CONFIGURATION = 1
    TX = 2

class RF_Sensor_Physical_Texas_Instruments(RF_Sensor_Physical):
    """
    Physical RF sensor for the Texas Instruments branded hardware.
    """

    def __init__(self, arguments, thread_manager, location_callback,
                 receive_callback, valid_callback, usb_manager=None):
        """
        Initialize the physical RF sensor for Texas Instruments branded hardware.
        """

        super(RF_Sensor_Physical_Texas_Instruments, self).__init__(arguments, thread_manager,
                                                                   location_callback,
                                                                   receive_callback,
                                                                   valid_callback,
                                                                   usb_manager=usb_manager)

        self._address = str(self._id)
        self._joined = True
        self._polling_time = 0.0

        self._packet_length = self._settings.get("packet_length")
        self._reset_delay = self._settings.get("reset_delay")
        self._polling_delay = self._settings.get("polling_delay")
        self._shift_minimum = self._settings.get("shift_minimum")
        self._shift_maximum = self._settings.get("shift_maximum")

        # UART connection pins for RX, TX, RTS, CTS and reset. We use board pin
        # numbering. The pins must correspond to the GPIO pins that support RXD0/TXD0 on
        # ALT0 and RTS0/CTS0 on ALT3. Refer to http://elinux.org/RPi_BCM2835_GPIOs for an
        # extensive overview.
        self._pins = {
            "rx_pin": self._settings.get("rx_pin"),
            "tx_pin": self._settings.get("tx_pin"),
            "rts_pin": self._settings.get("rts_pin"),
            "cts_pin": self._settings.get("cts_pin"),
            "reset_pin": self._settings.get("reset_pin")
        }

    @property
    def type(self):
        """
        Get the type of the RF sensor.

        The type is equal to the name of the settings group.
        """

        return "rf_sensor_physical_texas_instruments"

    def activate(self):
        """
        Activate the sensor to start sending and receiving packets.
        """

        # We need this because we only want the last part of this method
        # to be executed when the sensor originally was not activated.
        originally_activated = self._activated

        super(RF_Sensor_Physical_Texas_Instruments, self).activate()

        if not originally_activated:
            self._synchronize()

    def start(self):
        self._polling_time = time.time()

        super(RF_Sensor_Physical_Texas_Instruments, self).start()

    def discover(self, callback):
        """
        Discover all RF sensors in the network. The `callback` function is
        called when an RF sensor reports its identity.
        """

        super(RF_Sensor_Physical_Texas_Instruments, self).discover(callback)

        # Send a ping/pong packet to all sensors in the network.
        for index in xrange(1, self._number_of_sensors + 1):
            packet = Packet()
            packet.set("specification", "ping_pong")
            packet.set("sensor_id", index)

            self._send_tx_frame(packet, index)

    def _setup(self):
        """
        Setup the RF sensor by opening the connection to it.
        """

        if self._id > 0:
            # Set up alternative modes for the UART pins. The RX/TX pins are here for
            # sanity, but might help in ensuring that these pins have the correct
            # alternative modes for some Raspberry Pi devices.
            wiringpi = WiringPi()
            if not wiringpi.is_raspberry_pi:
                raise RuntimeError("Must be run on a Raspberry Pi")

            wiringpi.module.pinModeAlt(self._pins["rx_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT0)
            wiringpi.module.pinModeAlt(self._pins["tx_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT0)
            wiringpi.module.pinModeAlt(self._pins["rts_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT3)
            wiringpi.module.pinModeAlt(self._pins["cts_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT3)

            # Open the serial connection.
            self._connection = self._usb_manager.get_cc2530_device()

            # Reset the CC2530 device.
            wiringpi.module.pinMode(self._pins["reset_pin"], wiringpi.module.OUTPUT)
            wiringpi.module.digitalWrite(self._pins["reset_pin"], 0)
            time.sleep(self._reset_delay)
            wiringpi.module.digitalWrite(self._pins["reset_pin"], 1)

            self._connection.reset_input_buffer()
        else:
            # The ground station is a CC2531 device, which simply uses USB.
            self._connection = self._usb_manager.get_cc2531_device()

        # Configure the device using a configuration packet.
        self._connection.write(struct.pack("<BB", CC2530_Packet.CONFIGURATION, self._id))

    def _loop_body(self):
        """
        Body of the sensor loop.

        This is extracted into a separate method to make testing easier, as well
        as for keeping the `_loop` implementation in the base class.
        """

        self._receive()

        # We should have received a packet from another sensor. If not, it is very
        # likely that their schedules interfere because of their activation time.
        # Resolve this by randomly shifting the schedule. This will be corrected
        # automatically by the synchronization method.
        if self._started and self._id > 0 and time.time() - self._polling_time > self._polling_delay:
            self._scheduler.shift(random.uniform(self._shift_minimum, self._shift_maximum))
            self._scheduler.update()
            self._polling_time = time.time()

        super(RF_Sensor_Physical_Texas_Instruments, self)._loop_body()

    def _send_tx_frame(self, packet, to=None):
        """
        Send a TX frame with `packet` as payload `to` another sensor.
        """

        super(RF_Sensor_Physical_Texas_Instruments, self)._send_tx_frame(packet, to)

        serialized_packet = packet.serialize()
        serialized_packet_length = len(serialized_packet)

        serialized_packet_format = "<BBB{}s".format(self._packet_length)
        payload = struct.pack(serialized_packet_format, CC2530_Packet.TX, to,
                              serialized_packet_length, serialized_packet)
        self._connection.write(payload)
        self._connection.flush()

    def _receive(self, packet=None):
        """
        Receive and process a `packet` from another sensor in the network.
        """

        # Read the UART packet from the serial connection (if available) and parse it.
        serialized_packet_format = "<B{}sb".format(self._packet_length)
        serialized_packet_length = struct.calcsize(serialized_packet_format)
        if self._connection.in_waiting < serialized_packet_length:
            return

        uart_packet = self._connection.read(size=serialized_packet_length)
        length, data, rssi = struct.unpack(serialized_packet_format, uart_packet)
        data = data[0:length]

        # Convert the packet to a `Packet` object according to specifications.
        packet = Packet()
        packet.unserialize(data)

        self._polling_time = time.time()
        try:
            self._process(packet, rssi=rssi)
        except ValueError:
            # Any errors must be logged, but must not crash the process.
            self._thread_manager.log(self.type)

    def _process(self, packet, rssi=None, **kwargs):
        """
        Process a `Packet` object `packet`.
        """

        if rssi is None:
            raise TypeError("RSSI value must be provided")

        specification = packet.get("specification")

        if self._id == 0:
            # Handle a ping/pong packet.
            if specification == "ping_pong":
                self._discovery_callback({
                    "id": packet.get("sensor_id"),
                    "address": str(packet.get("sensor_id"))
                })
                return

        # Respond to a ping/pong request.
        if specification == "ping_pong":
            self._send_tx_frame(packet, 0)
            return

        is_broadcast = super(RF_Sensor_Physical_Texas_Instruments, self)._process(packet, rssi=rssi)
        if is_broadcast:
            self._process_rssi_broadcast_packet(packet, rssi=rssi)

    def _process_rssi_broadcast_packet(self, packet, rssi=None, **kwargs):
        """
        Process a `Packet` object `packet` that has been created according to
        the "rssi_broadcast" specification.
        """

        if rssi is None:
            raise TypeError("RSSI value must be provided")

        packet = super(RF_Sensor_Physical_Texas_Instruments, self)._process_rssi_broadcast_packet(packet,
                                                                                                  rssi=rssi)
        packet.set("rssi", rssi)
        self._packets.append(packet)
