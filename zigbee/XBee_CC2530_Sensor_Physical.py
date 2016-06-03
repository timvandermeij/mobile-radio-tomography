# TODO:
# - Implement synchronous NTP (abstraction into class to avoid duplication)
# - Implement `RF_Sensor` abstraction, remove `self._data` and rename to `CC2530_Sensor_Physical`
# - Figure out ground station and blocking reads/writes
# - Write tests

import os
import struct
import subprocess
import time
import thread
import wiringpi
from XBee_Packet import XBee_Packet
from XBee_Sensor import XBee_Sensor, SensorClosedError

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

class XBee_CC2530_Sensor_Physical(XBee_Sensor):
    def __init__(self, arguments, thread_manager, usb_manager,
                 location_callback, receive_callback, valid_callback):
        """
        Initialize the physical XBee CC2530 sensor. We use the CC2530 sensor
        for exchanging packets and performing RSSI measurements, but the
        data that we transfer is packed as XBee packets.
        """

        self._type = "xbee_cc2530_sensor_physical"

        super(XBee_CC2530_Sensor_Physical, self).__init__(arguments, thread_manager,
                                                          usb_manager, location_callback,
                                                          receive_callback, valid_callback)

        self._data = []
        self._serial_connection = None
        self._synchronized = False

        self._packet_length = self._settings.get("packet_length")
        self._reset_delay = self._settings.get("reset_delay")

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

    def setup(self):
        """
        Setup the serial connection.
        """

        # Open and close the serial connection so that the UART buffers are correctly 
        # cleared. This is required to not receive only zeroes from the CC2530 device.
        self._serial_connection = self._usb_manager.get_cc2530_device()
        self._serial_connection.close()

        # Set up alternative modes for the UART pins. The RX/TX pins are here for
        # sanity, but might help in ensuring that these pins have the correct
        # alternative modes for some Raspberry Pi devices.
        wiringpi.wiringPiSetupPhys()
        wiringpi.pinModeAlt(self._pins["rx_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT0)
        wiringpi.pinModeAlt(self._pins["tx_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT0)
        wiringpi.pinModeAlt(self._pins["rts_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT3)
        wiringpi.pinModeAlt(self._pins["cts_pin"], Raspberry_Pi_GPIO_Pin_Mode.ALT3)

        # Reopen the serial connection.
        self._serial_connection = self._usb_manager.get_cc2530_device()

        # Reset the CC2530 device.
        wiringpi.pinMode(self._pins["reset_pin"], wiringpi.OUTPUT)
        wiringpi.digitalWrite(self._pins["reset_pin"], 0)
        time.sleep(self._reset_delay)
        wiringpi.digitalWrite(self._pins["reset_pin"], 1)

        # Configure the CC2530 device using a configuration packet.
        self._serial_connection.reset_input_buffer()
        self._serial_connection.write(struct.pack("<BB", CC2530_Packet.CONFIGURATION, self._id))

    def activate(self):
        """
        Activate the sensor to send and receive packets.
        """

        super(XBee_CC2530_Sensor_Physical, self).activate()

        if not self._active:
            self._active = True

            if self._serial_connection is None:
                self.setup()

            thread.start_new_thread(self._loop, ())

    def _loop(self):
        """
        Execute the sensor loop. This runs in a separate thread.
        """

        try:
            while self._active:
                self._receive(None)

                # If the sensor has been activated, this loop will only send
                # enqueued custom packets. If the sensor has been started, we
                # stop sending custom packets and start performing signal
                # strength measurements.
                if not self._started:
                    self._send_custom_packets()
                    time.sleep(self._custom_packet_delay)
                elif self._id > 0 and time.time() >= self._next_timestamp:
                    self._next_timestamp = self._scheduler.get_next_timestamp()
                    self._send()

                time.sleep(self._loop_delay)
        except SensorClosedError:
            # Serial connection was removed by deactivate, so end the loop.
            pass
        except:
            super(XBee_CC2530_Sensor_Physical, self).interrupt()

    def deactivate(self):
        """
        Deactivate the sensor and close the serial connection.
        """

        super(XBee_CC2530_Sensor_Physical, self).deactivate()

        if self._active or self._serial_connection is not None:
            self._active = False

            if self._serial_connection is not None:
                self._serial_connection = None

    def discover(self, callback):
        """
        Discover other XBee devices in the network.

        This method is only used on the ground station in the control panel
        to refresh the status of the other XBee devices.
        """

        # Register the discovery callback.
        self._discovery_callback = callback

        # Construct the CC2530 ping/pong packet.
        packet = XBee_Packet()
        packet.set("specification", "cc2530_ping_pong")

        # Send a ping to all sensors in the network.
        for index in xrange(1, self._number_of_sensors + 1):
            packet.set("sensor_id", index)
            self._send_tx_frame(packet, index)

    def _ntp(self, packet):
        """
        Perform the NTP (network time protocol) algorithm to synchronize
        the sensor's clock with the ground sensor's clock.

        Refer to the original paper "Internet time synchronization: the
        network time protocol" by David L. Mills (IEEE, 1991) for more
        information.
        """

        # Calculate the clock offset.
        a = packet.get("timestamp_2") - packet.get("timestamp_1")
        b = packet.get("timestamp_3") - packet.get("timestamp_4")
        clock_offset = float(a + b) / 2

        # Apply the offset to the current clock to synchronize.
        synchronized = time.time() + clock_offset

        # Update the system clock with the synchronized clock.
        with open(os.devnull, 'w') as FNULL:
            subprocess.call(["date", "-s", "@{}".format(synchronized)],
                            stdout=FNULL, stderr=FNULL)

        self._synchronized = True
        return clock_offset

    def _send(self):
        """
        Send a packet to each other sensor in the network.
        """

        # Create and send the RSSI broadcast packets.
        packet = self._make_rssi_broadcast_packet()

        for index in xrange(1, self._number_of_sensors + 1):
            if index == self._id:
                continue

            self._send_tx_frame(packet, index)

        # Send the sweep data to the ground sensor and clear the list
        # for the next round.
        for packet in self._data:
            self._send_tx_frame(packet, 0)

        self._data = []

    def _send_tx_frame(self, packet, to=None):
        """
        Send a TX frame to another sensor.
        """

        super(XBee_CC2530_Sensor_Physical, self)._send_tx_frame(packet, to)

        serialized_packet = packet.serialize()
        serialized_packet_length = len(serialized_packet)

        serialized_packet_format = "<BBB{}s".format(self._packet_length)
        payload = struct.pack(serialized_packet_format, CC2530_Packet.TX, to,
                              serialized_packet_length, serialized_packet)
        self._serial_connection.write(payload)

    def _receive(self, raw_packet):
        """
        Receive and process a raw packet from another sensor in the network.
        """

        # Read the UART packet from the serial connection and parse it.
        serialized_packet_format = "<B{}sb".format(self._packet_length)
        uart_packet = self._serial_connection.read(size=struct.calcsize(serialized_packet_format))
        length, data, rssi = struct.unpack(serialized_packet_format, uart_packet)
        data = data[0:length]

        # Convert the raw packet to an XBee packet according to specifications.
        packet = XBee_Packet()
        packet.unserialize(data)

        # Check whether the packet is not private and pass it along to the 
        # receive callback.
        if self._check_receive(packet):
            return

        # Handle NTP synchronization packets.
        if packet.get("specification") == "ntp":
            if packet.get("timestamp_2") == 0:
                packet.set("timestamp_2", time.time())
                packet.set("timestamp_3", time.time())
                self._send_tx_frame(packet, packet.get("sensor_id"))
            else:
                packet.set("timestamp_4", time.time())
                self._ntp(packet)

            return

        if self._id == 0:
            # Handle CC2530 ping/pong packets.
            if packet.get("specification") == "cc2530_ping_pong":
                self._discovery_callback({
                    "id": packet.get("sensor_id"),
                    "address": packet.get("sensor_id")
                })

            # Handle an RSSI ground station packet.
            if self._buffer is not None:
                self._buffer.put(packet)

            return

        # Handle a received RSSI broadcast packet.
        self._process_rssi_broadcast_packet(packet, rssi=rssi)

    def _process_rssi_broadcast_packet(self, packet, rssi=None):
        """
        Process a received packet with RSSI measurements.
        """

        # Synchronize the scheduler using the timestamp in the packet.
        self._next_timestamp = self._scheduler.synchronize(packet)

        # Create the packet for the ground station.
        if rssi is None:
            raise ValueError("Missing RSSI value for ground station packet")

        ground_station_packet = self._make_rssi_ground_station_packet(packet)
        ground_station_packet.set("rssi", rssi)
        self._data.append(ground_station_packet)
