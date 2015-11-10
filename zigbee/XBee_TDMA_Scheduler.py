import time
from ..settings import Arguments, Settings

class XBee_TDMA_Scheduler(object):
    def __init__(self, sensor_id, settings):
        """
        Initialize the TDMA scheduler with the sensor ID.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_tdma_scheduler")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self.id = sensor_id
        self.timestamp = 0
        self.number_of_sensors = self.settings.get("number_of_sensors")
        self.sweep_delay = self.settings.get("sweep_delay")

    def get_next_timestamp(self):
        """
        Get the next timestamp for transmitting packets.
        """

        if self.timestamp == 0:
            self.timestamp = time.time() + ((float(self.id) / self.number_of_sensors) *
                             self.sweep_delay)
        else: 
            self.timestamp += self.sweep_delay
        
        return self.timestamp

    def synchronize(self, packet):
        """
        Synchronize the scheduler after receiving a packet from another sensor
        in the network. The transmission timestamp of this sensor is the received
        transmission timestamp plus the number of slots inbetween that sensor
        and this sensor.
        """

        slot_time = float(self.sweep_delay) / self.number_of_sensors
        from_sensor = int(packet.get("sensor_id"))
        timestamp = float(packet.get("timestamp"))

        if from_sensor < self.id:
            self.timestamp = timestamp + ((self.id - from_sensor) * slot_time)
        else:
            # Calculate how much time remains to complete the current sweep.
            completed_round = (self.number_of_sensors - from_sensor + 1) * slot_time
            self.timestamp = timestamp + completed_round + ((self.id - 1) * slot_time)

        return self.timestamp
