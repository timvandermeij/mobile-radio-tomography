import unittest
from ..reconstruction.Dataset_Buffer import Dataset_Buffer

class TestReconstructionDatasetBuffer(unittest.TestCase):
    def setUp(self):
        # The sensor ID and RSSI values come from the CSV file.
        self.sensor_id = 5
        self.rssi = [
            -63, -62, -60, -59, -52, -45, -58, -60, -61, -52, -58, -54, -60, -60,
            -62, -70, -60, -62, -66, -66, -67, -70, -68, -61, -62, -62, -54, -60
        ]

        # The size and positions come from the Utah dataset specification.
        self.size = [21, 21]
        self.positions = [
            (0, 0), (0, 3), (0, 6), (0, 9), (0, 12), (0, 15), (0, 18),
            (0, 21), (3, 21), (6, 21), (9, 21), (12, 21), (15, 21), (18, 21),
            (21, 21), (21, 18), (21, 15), (21, 12), (21, 9), (21, 6), (21, 3),
            (21, 0), (18, 0), (15, 0), (12, 0), (9, 0), (6, 0), (2, 0)
        ]

    def test_initialization(self):
        # Dataset buffers are regular buffers with the exception that they
        # populate the queue with XBee packets read from a CSV data file.
        # Verify that these are set correctly upon initialization.
        options = {
            "file": "tests/reconstruction/dataset.csv"
        }
        dataset_buffer = Dataset_Buffer(options)

        self.assertEqual(dataset_buffer.number_of_sensors, len(self.positions))
        self.assertEqual(dataset_buffer.origin, [0, 0])
        self.assertEqual(dataset_buffer.size, self.size)

        # One data point is ignored because a sensor cannot send to itself.
        self.assertEqual(dataset_buffer.count(), len(self.positions) - 1)

        for index in range(len(self.positions)):
            if index == self.sensor_id:
                continue

            packet = dataset_buffer.get()
            self.assertEqual(packet.get_all(), {
                "specification": "rssi_ground_station",
                "sensor_id": self.sensor_id + 1,
                "from_latitude": self.positions[index][0],
                "from_longitude": self.positions[index][1],
                "from_valid": True,
                "to_latitude": self.positions[self.sensor_id][0],
                "to_longitude": self.positions[self.sensor_id][1],
                "to_valid": True,
                "rssi": self.rssi[index]
            })

        self.assertEqual(dataset_buffer.get(), None)
        self.assertEqual(dataset_buffer.count(), 0)
