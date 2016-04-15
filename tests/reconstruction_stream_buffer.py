import unittest
from ..reconstruction.Stream_Buffer import Stream_Buffer

class TestReconstructionStreamBuffer(unittest.TestCase):
    def test_initialization(self):
        # Stream buffers are regular buffers with the exception that they
        # use options to set the number of sensors, origin and size.
        # Verify that these are set correctly upon initialization.
        options = {
            "number_of_sensors": 42,
            "origin": [1, 1],
            "size": [15, 15]
        }
        stream_buffer = Stream_Buffer(options)

        self.assertEqual(stream_buffer.number_of_sensors, options["number_of_sensors"])
        self.assertEqual(stream_buffer.origin, options["origin"])
        self.assertEqual(stream_buffer.size, options["size"])
