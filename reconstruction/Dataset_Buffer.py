import csv
from Buffer import Buffer
from ..zigbee.XBee_Packet import XBee_Packet

class Dataset_Buffer(Buffer):
    def __init__(self, options=None):
        """
        Initialize the dataset buffer object.
        """

        super(Dataset_Buffer, self).__init__(options)

        # Read the provided dataset file. The CSV file is a radio tomographic
        # imaging dataset provided by the University of Utah. Refer to
        # http://span.ece.utah.edu/rti-data-set for more information on how the
        # dataset is structured. The size and positions below originate from the
        # README file provided with the dataset.
        size = [21, 21]
        positions = [
            (0, 0), (0, 3), (0, 6), (0, 9), (0, 12), (0, 15), (0, 18),
            (0, 21), (3, 21), (6, 21), (9, 21), (12, 21), (15, 21), (18, 21),
            (21, 21), (21, 18), (21, 15), (21, 12), (21, 9), (21, 6), (21, 3),
            (21, 0), (18, 0), (15, 0), (12, 0), (9, 0), (6, 0), (2, 0)
        ]

        with open(options["file"], "r") as dataset_file:
            data = csv.reader(dataset_file)

            self._size = size

            for line in data:
                reporting_sensor_id = int(line[0])
                reporting_sensor_position = positions[reporting_sensor_id]

                for index, position in enumerate(positions):
                    # Ignore entries that indicate sending to ourselves.
                    if index == reporting_sensor_id:
                        continue

                    column = index + 1

                    xbee_packet = XBee_Packet()
                    xbee_packet.set("specification", "rssi_ground_station")
                    xbee_packet.set("sensor_id", reporting_sensor_id)
                    xbee_packet.set("from_latitude", position[0])
                    xbee_packet.set("from_longitude", position[1])
                    xbee_packet.set("from_valid", True)
                    xbee_packet.set("to_latitude", reporting_sensor_position[0])
                    xbee_packet.set("to_longitude", reporting_sensor_position[1])
                    xbee_packet.set("to_valid", True)
                    xbee_packet.set("rssi", int(line[column]))
                    self.put(xbee_packet)
