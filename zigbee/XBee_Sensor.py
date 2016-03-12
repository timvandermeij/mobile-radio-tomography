import time
from ..core.Threadable import Threadable
from XBee_Packet import XBee_Packet

class XBee_Sensor(Threadable):
    def __init__(self, thread_manager, location_callback, receive_callback):
        super(XBee_Sensor, self).__init__("xbee_sensor", thread_manager)

        if not hasattr(location_callback, "__call__"):
            raise TypeError("Location callback is not callable")

        if not hasattr(receive_callback, "__call__"):
            raise TypeError("Receive callback is not callable")

        self._location_callback = location_callback
        self._receive_callback = receive_callback

    def enqueue(self, packet, to=None):
        raise NotImplementedError("Subclasses must implement `enqueue(packet, to=None)`")

    def _send(self):
        raise NotImplementedError("Subclasses must implement `_send()`")

    def _receive(self, packet):
        raise NotImplementedError("Subclasses must implement `_receive(packet)`")

    def check_receive(self, packet):
        """
        Check whether the given `packet` should be given to the receive callback
        rather than handling it internally.

        The return value is `False` if the packet should be handled internally,
        otherwise it is `True` and the calling method should stop handling it.
        """

        if not packet.is_private():
            self._receive_callback(packet)
            return True

        return False

    def make_rssi_broadcast_packet(self):
        """
        Create an XBee_Packet object containing current location data.

        The resulting packet is only missing the XBee ID of the current XBee.
        """

        location = self._location_callback()
        packet = XBee_Packet()
        packet.set("specification", "rssi_broadcast")
        packet.set("latitude", location[0])
        packet.set("longitude", location[1])
        packet.set("timestamp", time.time())

        return packet

    def make_ground_station_packet(self, rssi_packet):
        """
        Create an XBee_Packet object containing location data of the current
        XBee and data from an XBee_Packet `rssi_packet`. The `rssi_packet`
        must have an "rssi_broadcast" specification.

        The resulting packet is only missing RSSI information.

        The packet can then be sent to the ground station as an indication of
        the signal strength between the XBee that sended the `rssi_packet` and
        the current XBee.
        """

        location = self._location_callback()
        ground_station_packet = XBee_Packet()
        ground_station_packet.set("specification", "rssi_ground_station")
        ground_station_packet.set("from_latitude", rssi_packet.get("latitude"))
        ground_station_packet.set("from_longitude", rssi_packet.get("longitude"))
        ground_station_packet.set("to_latitude", location[0])
        ground_station_packet.set("to_longitude", location[1])

        return ground_station_packet

