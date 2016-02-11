import json
import Queue
from ..zigbee.XBee_Packet import XBee_Packet

class Dump_Reader(object):
    def __init__(self, filename):
        """
        Initialize the dump reader object.
        """

        self._filename = filename

        self._size = [0, 0]
        self._packets = Queue.Queue()

        self._read()

    def _read(self):
        """
        Read the provided dump file. A dump file is a JSON file with the following structure:

        * size: a list containing the width and height of the network
        * packets: a list containing one list per packet, where each packet list contains the
                   data from the XBee packet specification "rssi_ground_station" (in order)
        """

        with open(self._filename, "r") as dump:
            data = json.load(dump)
            size = data["size"]
            packets = data["packets"]

            self._size = size
            for packet in packets:
                xbee_packet = XBee_Packet()
                xbee_packet.set("specification", "rssi_ground_station")
                xbee_packet.set("from_latitude", packet[0])
                xbee_packet.set("from_longitude", packet[1])
                xbee_packet.set("to_latitude", packet[2])
                xbee_packet.set("to_longitude", packet[3])
                xbee_packet.set("rssi", packet[4])
                self._packets.put(xbee_packet)

    def get_size(self):
        """
        Get the size of the network.
        """

        return self._size

    def get_packet(self):
        """
        Get a packet from the packet queue or None if the queue is empty.
        """

        if self._packets.empty():
            return None

        return self._packets.get()

    def count_packets(self):
        """
        Count the number of packets in the packet queue.
        """

        return self._packets.qsize()
