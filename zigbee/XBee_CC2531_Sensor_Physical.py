import random
import struct
from XBee_Sensor_Physical import XBee_Sensor_Physical

class CC2531_Packet(object):
    CONFIGURATION = 1
    TX = 2

class XBee_CC2531_Sensor_Physical(XBee_Sensor_Physical):
    def __init__(self, arguments, thread_manager, usb_manager,
                 location_callback, receive_callback, valid_callback):
        """
        Initialize the physical XBee sensor working with the CC2531
        USB dongle for RSSI measurements.
        """

        super(XBee_CC2531_Sensor_Physical, self).__init__(arguments, thread_manager,
                                                          usb_manager, location_callback,
                                                          receive_callback, valid_callback)

    def setup(self):
        """
        Setup the serial connection and identify the sensor.

        Furthermore we send a configuration packet to the CC2531
        USB dongle to let it know its sensor ID such that this ID
        can be put into TX packets.
        """

        super(XBee_CC2531_Sensor_Physical, self).setup()

        self._cc2531_serial_connection = self._usb_manager.get_cc2531_device()
        self._cc2531_serial_connection.write(struct.pack("<HH", CC2531_Packet.CONFIGURATION, self._id))

    def _send(self):
        """
        Send a packet to each other sensor in the network.
        """

        super(XBee_CC2531_Sensor_Physical, self)._send()

        # Perform RSSI measurements using the CC2531 USB dongles.
        for destination in xrange(1, self._number_of_sensors + 1):
            if destination == self._id:
                continue

            self._cc2531_serial_connection.write(struct.pack("<HH", CC2531_Packet.TX, destination))

    def _process_rssi_broadcast_packet(self, packet):
        """
        Process a received packet with RSSI measurements.
        """

        # Synchronize the scheduler using the timestamp in the packet.
        self._next_timestamp = self._scheduler.synchronize(packet)

        # Create the packet for the ground station.
        rssi_packet = self._cc2531_serial_connection.read(size=4)
        from_id, rssi = struct.unpack("<Hh", rssi_packet)

        if from_id != packet.get("sensor_id"):
            return

        ground_station_packet = self._make_rssi_ground_station_packet(packet)
        ground_station_packet.set("rssi", rssi)
        self._data[random.randint(1, 255)] = ground_station_packet
