import json
from Buffer import Buffer
from ..zigbee.XBee_Packet import XBee_Packet

class Dump_Buffer(Buffer):
    def __init__(self, options=None):
        """
        Initialize the dump buffer object.
        """

        super(Dump_Buffer, self).__init__(options)

        if options is None:
            raise ValueError("No filename has been provided.")

        self._origin = [0, 0]
        self._size = [0, 0]

        # Read the provided dump file. The JSON file has the following structure:
        #
        # - origin: a list containing the coordinates of the network's origin
        # - size: a list containing the width and height of the network
        # - packets: a list containing one list per packet, where each packet list
        #            contains the data from the XBee packet specification
        #            "rssi_ground_station" (in order)
        with open(options["filename"], "r") as dump_file:
            data = json.load(dump_file)

            self._origin = data["origin"]
            self._size = data["size"]

            for packet in data["packets"]:
                xbee_packet = XBee_Packet()
                xbee_packet.set("specification", "rssi_ground_station")
                xbee_packet.set("sensor_id", packet[0])
                xbee_packet.set("from_latitude", packet[1])
                xbee_packet.set("from_longitude", packet[2])
                xbee_packet.set("to_latitude", packet[3])
                xbee_packet.set("to_longitude", packet[4])
                xbee_packet.set("rssi", packet[5])
                self.put(xbee_packet)

    @property
    def origin(self):
        return self._origin

    @property
    def size(self):
        return self._size
