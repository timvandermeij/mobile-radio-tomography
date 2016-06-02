# TODO:
# - Finish initialization (WiringPi)
# - Implement synchronous NTP (abstraction into class to avoid duplication)
# - Implement discovery (ping/pong packets)
# - Implement `RF_Sensor` abstraction, remove `self._data` and rename to `CC2530_Sensor_Physical`
# - Figure out ground station and blocking reads/writes
# - Write tests

import os
import serial
import struct
import subprocess
import time
import thread
from XBee_Sensor import XBee_Sensor, SensorClosedError

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

    def setup(self):
        """
        Setup the serial connection.
        """

        self._serial_connection = self._usb_manager.get_cc2530_device()
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

        pass

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
        packet.set("rssi", rssi)

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

        # Handle an RSSI ground station packet.
        if self._id == 0:
            if self._buffer is not None:
                self._buffer.put(packet)

            return

        # Handle a received RSSI broadcast packet.
        self._process_rssi_broadcast_packet(packet)

    def _process_rssi_broadcast_packet(self, packet):
        """
        Process a received packet with RSSI measurements.
        """

        # Synchronize the scheduler using the timestamp in the packet.
        self._next_timestamp = self._scheduler.synchronize(packet)

        # Create the packet for the ground station.
        ground_station_packet = self._make_rssi_ground_station_packet(packet)
        ground_station_packet.set("rssi", packet.get("rssi"))
        self._data.append(ground_station_packet)
