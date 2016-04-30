import csv
from Buffer import Buffer
from ..zigbee.XBee_Packet import XBee_Packet

class Dataset_Buffer(Buffer):
    def __init__(self, settings=None):
        """
        Initialize the dataset buffer object.
        """

        super(Dataset_Buffer, self).__init__(settings)

        # Read the provided dataset file. The CSV file is a radio tomographic
        # imaging dataset provided by the University of Utah. Refer to
        # http://span.ece.utah.edu/rti-data-set for more information on how the
        # dataset is structured. The size and positions below originate from the
        # README file provided with the dataset.
        self._positions = [
            (0, 0), (0, 3), (0, 6), (0, 9), (0, 12), (0, 15), (0, 18),
            (0, 21), (3, 21), (6, 21), (9, 21), (12, 21), (15, 21), (18, 21),
            (21, 21), (21, 18), (21, 15), (21, 12), (21, 9), (21, 6), (21, 3),
            (21, 0), (18, 0), (15, 0), (12, 0), (9, 0), (6, 0), (2, 0)
        ]
        self._number_of_sensors = len(self._positions)
        self._size = (21, 21)

        # Read the data from the empty network (for calibration).
        calibration_filename = settings.get("dataset_calibration_file")
        with open(calibration_filename, "r") as dataset_calibration_file:
            for line in csv.reader(dataset_calibration_file):
                destination_id = int(line[0])

                for source_id in range(self._number_of_sensors):
                    # Ignore entries that indicate sending to ourselves.
                    if source_id == destination_id:
                        continue

                    source = self._positions[source_id]
                    destination = self._positions[destination_id]
                    rssi = int(line[source_id + 1])

                    self._calibration[(source, destination)] = rssi

        # Read the data from the nonempty network.
        with open(settings.get("dataset_file"), "r") as dataset_file:
            for line in csv.reader(dataset_file):
                destination_id = int(line[0])

                for source_id in range(self._number_of_sensors):
                    # Ignore entries that indicate sending to ourselves.
                    if source_id == destination_id:
                        continue

                    source = self._positions[source_id]
                    destination = self._positions[destination_id]
                    rssi = int(line[source_id + 1])

                    self.put([source, destination, rssi])

    def get(self):
        """
        Get a packet from the buffer (or None if the queue is empty). We create
        the XBee packet object from the list on demand (as further explained
        in the `put` method). The return value is a tuple of the original packet
        and the calibrated RSSI value.
        """

        if self._queue.empty():
            return None

        packet = self._queue.get()

        source = packet[0]
        destination = packet[1]
        destination_id = self._positions.index(destination) + 1
        rssi = packet[2]

        xbee_packet = XBee_Packet()
        xbee_packet.set("specification", "rssi_ground_station")
        xbee_packet.set("sensor_id", destination_id)
        xbee_packet.set("from_latitude", source[0])
        xbee_packet.set("from_longitude", source[1])
        xbee_packet.set("from_valid", True)
        xbee_packet.set("to_latitude", destination[0])
        xbee_packet.set("to_longitude", destination[1])
        xbee_packet.set("to_valid", True)
        xbee_packet.set("rssi", rssi)

        calibrated_rssi = rssi - self._calibration[(source, destination)]

        return (xbee_packet, calibrated_rssi)

    def put(self, packet):
        """
        Put a packet into the buffer. The difference with the base class method
        is that a packet is not an XBee packet object, but instead a list that
        contains the source sensor ID, the destination sensor ID and the RSSI
        value. XBee packet objects will be generated from this information on
        demand in the `get` method. This optimization is required because the
        datasets typically contain many rows and columns, making creating all
        XBee packet objects at once very time-consuming.
        """

        if not isinstance(packet, list) or len(packet) != 3:
            raise ValueError("The provided packet is not a valid list.")

        self._queue.put(packet)
