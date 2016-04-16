import json
from Buffer import Buffer
from ..zigbee.XBee_Packet import XBee_Packet

class Dump_Buffer(Buffer):
    def __init__(self, options=None):
        """
        Initialize the dump buffer object.
        """

        super(Dump_Buffer, self).__init__(options)

        # Read the provided dump file. The JSON file has the following structure:
        #
        # - number_of_sensors: number of sensors in the network (excluding ground station)
        # - origin: a list containing the coordinates of the network's origin
        # - size: a list containing the width and height of the network
        # - packets: a list containing one list per packet, where each packet list
        #            contains the data from the XBee packet specification
        #            "rssi_ground_station" (in order)
        with open(options["file"], "r") as dump_file:
            data = json.load(dump_file)

            self._number_of_sensors = data["number_of_sensors"]
            self._origin = data["origin"]
            self._size = data["size"]

            for packet in data["packets"]:
                self.put(packet)

    def get(self):
        """
        Get a packet from the buffer (or None if the queue is empty). We create
        the XBee packet object from the list on demand (as further explained
        in the `put` method).
        """

        if self._queue.empty():
            return None

        packet = self._queue.get()

        xbee_packet = XBee_Packet()
        xbee_packet.set("specification", "rssi_ground_station")
        xbee_packet.set("sensor_id", packet[0])
        xbee_packet.set("from_latitude", packet[1])
        xbee_packet.set("from_longitude", packet[2])
        xbee_packet.set("from_valid", packet[3])
        xbee_packet.set("to_latitude", packet[4])
        xbee_packet.set("to_longitude", packet[5])
        xbee_packet.set("to_valid", packet[6])
        xbee_packet.set("rssi", packet[7])

        return xbee_packet

    def put(self, packet):
        """
        Put a packet into the buffer. The difference with the base class method
        is that a packet is not an XBee packet object, but instead a list that
        contains the data from the XBee packet fields in order. XBee packet
        objects will be generated from this information on demand in the `get`
        method. This optimization is required because the dumps typically
        contain many measurements, making creating all XBee packet objects at
        once very time-consuming.
        """

        if not isinstance(packet, list) or len(packet) != 8:
            raise ValueError("The provided packet is not a valid list.")

        self._queue.put(packet)
