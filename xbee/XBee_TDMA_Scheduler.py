import time

class XBee_TDMA_Scheduler(object):
    def __init__(self, settings, id):
        self.settings = settings
        self.id = id
        self.timestamp = 0

    def get_next_timestamp(self):
        # Get the next timestamp for starting transmission of packets.
        if self.timestamp == 0:
            self.timestamp = time.time() + ((self.id / self.settings.get("number_of_sensors")) *
                             self.settings.get("sweep_delay"))
        else: 
            self.timestamp += self.settings.get("sweep_delay")
        
        return self.timestamp

    def synchronize(self, packet):
        # Synchronize the scheduler after receiving a packet from
        # another sensor in the network. The transmission timestamp of this
        # sensor is the received transmission timestamp plus the number of
        # slots inbetween that sensor and this sensor.
        slot_time = self.settings.get("sweep_delay") / self.settings.get("number_of_sensors")
        from_sensor = int(packet["from"])
        timestamp = float(packet["timestamp"])
        if from_sensor < self.id:
            self.timestamp = timestamp + ((self.id - from_sensor) * slot_time)
        else:
            # Calculate how much time remains to complete the current round.
            completed_round = (self.settings.get("number_of_sensors") - from_sensor + 1) * slot_time
            self.timestamp = timestamp + completed_round + ((self.id - 1) * slot_time)

        return self.timestamp
