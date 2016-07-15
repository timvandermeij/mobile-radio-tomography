import time
from ..settings import Arguments

class TDMA_Scheduler(object):
    def __init__(self, id, arguments):
        """
        Initialize the TDMA scheduler.
        """

        if isinstance(arguments, Arguments):
            self._settings = arguments.get_settings("zigbee_tdma_scheduler")
        else:
            raise TypeError("'arguments' must be an instance of Arguments")

        self._number_of_sensors = self._settings.get("number_of_sensors")
        self._sweep_delay = self._settings.get("sweep_delay")

        self._id = id
        self._timestamp = 0
        self._slot_time = float(self._sweep_delay) / self._number_of_sensors

    @property
    def id(self):
        """
        Get the ID of the sensor.
        """

        return self._id

    @id.setter
    def id(self, id):
        """
        Set the ID of the sensor.
        """

        self._id = id

    @property
    def timestamp(self):
        """
        Get the timestamp at which the sensor is allowed to send packets.
        """

        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        """
        Change the timestamp at which the sensor is allowed to send packets.

        If this is set to `0`, then the sensor is allowed to send packets, and
        the timestamp is corrected the next time the scheduler is updated.
        This value can be of use when the measurements are paused for a longer
        time, and we need to send at least one packet again to get back on
        schedule after restarting.
        """

        self._timestamp = value

    def update(self):
        """
        Update the timestamp for sending packets.
        """

        if self._timestamp == 0:
            self._timestamp = time.time() + ((float(self._id) / self._number_of_sensors) *
                                             self._sweep_delay)
        else: 
            self._timestamp += self._sweep_delay

    def synchronize(self, packet):
        """
        Synchronize the scheduler after receiving a `packet` from another sensor
        in the network. The transmission timestamp of this sensor is the received
        transmission timestamp plus the number of slots inbetween that sensor
        and this sensor.
        """

        from_sensor = int(packet.get("sensor_id"))
        timestamp = float(packet.get("timestamp"))

        if from_sensor < self._id:
            timestamp += (self._id - from_sensor) * self._slot_time
        else:
            # Calculate how much time remains to complete the current sweep.
            completed_round = (self._number_of_sensors - from_sensor + 1) * self._slot_time
            timestamp += completed_round + ((self._id - 1) * self._slot_time)

        # Only accept future timestamps.
        if timestamp > self._timestamp:
            self._timestamp = timestamp

    def shift(self, seconds):
        """
        Shift the schedule by a given number of `seconds`.

        This is useful for when the schedules of the RF sensors coincidentally
        overlap. Since the CC2530 devices cannot send and receive at the same
        time, this might cause a deadlock.
        """

        self._timestamp += seconds
