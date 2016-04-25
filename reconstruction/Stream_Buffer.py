import json
from Buffer import Buffer

class Stream_Buffer(Buffer):
    def __init__(self, options=None):
        """
        Initialize the stream buffer object.
        """

        super(Stream_Buffer, self).__init__(options)

        self._number_of_sensors = options["number_of_sensors"]
        self._origin = options["origin"]
        self._size = options["size"]

        self._calibrate = options["calibrate"]

        # Read the data from the empty network (for calibration).
        if not self._calibrate:
            with open(options["calibration_file"], "r") as stream_calibration_file:
                data = json.load(stream_calibration_file)

                for packet in data["packets"]:
                    source = (packet[1], packet[2])
                    destination = (packet[4], packet[5])

                    if packet[3] and packet[6]:
                        key = (source, destination)
                        if not key in self._calibration:
                            self._calibration[key] = packet[7]

    def get(self):
        """
        Get a packet from the buffer (or None if the queue is empty). The return
        value is a tuple of the original packet and the calibrated RSSI value.
        If calibration mode is enabled, however, we return the original RSSI
        value because there is no complete calibration yet.
        """

        if self._queue.empty():
            return None

        packet = self._queue.get()

        if self._calibrate:
            # We are in calibration mode. There is no complete calibration yet,
            # so return the original packet and original RSSI value.
            return (packet, packet.get("rssi"))

        source = (packet.get("from_latitude"), packet.get("from_longitude"))
        destination = (packet.get("to_latitude"), packet.get("to_longitude"))
        calibrated_rssi = packet.get("rssi") - self._calibration[(source, destination)]

        return (packet, calibrated_rssi)
