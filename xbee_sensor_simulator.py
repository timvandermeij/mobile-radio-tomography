import sys
import time
import json
import argparse
import socket
from random import randint
from settings.Settings import Settings

class TDMA_Scheduler(object):
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

class XBee_Sensor(object):
    def __init__(self, settings, id):
        # Initialize the sensor with its ID and a unique, non-blocking UDP socket.
        self.settings = settings
        self.id = id
        self.next_timestamp = 0
        self.scheduler = TDMA_Scheduler(self.settings, self.id)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.settings.get("ip"), self.settings.get("port") + self.id))
        self.socket.setblocking(0)

    def run(self):
        # Execute the sensor's main loop that constantly sends and receives packets.
        self.next_timestamp = self.scheduler.get_next_timestamp()
        while True:
            # Add a small delay to avoid 100% CPU usage due to the while loop.
            time.sleep(self.settings.get("loop_delay"))

            if time.time() >= self.next_timestamp:
                self._send()
                self.next_timestamp = self.scheduler.get_next_timestamp()

            self._receive()

    def _send(self):
        # Send packets to all other sensors.
        for i in range(1, self.settings.get("number_of_sensors") + 1):
            if i == self.id:
                continue

            packet = {
                "from": self.id,
                "to": i,
                "timestamp": time.time(),
                "rssi": -randint(1,60)
            }
            self.socket.sendto(json.dumps(packet), (self.settings.get("ip"), self.settings.get("port") + i))
            print("-> {} sending at {}...".format(self.id, packet["timestamp"]))

    def _receive(self):
        # Receive packets from all other sensors.
        try:
            packet = json.loads(self.socket.recv(self.settings.get("buffer_size")))
            self.next_timestamp = self.scheduler.synchronize(packet)
            print("{} receiving at {}...".format(self.id, time.time()))
        except socket.error:
            pass

def main(argv):
    settings = Settings("settings.json", "xbee_sensor_simulator")
    
    parser = argparse.ArgumentParser(description="Simulate packet communication in a WiFi sensor network.")
    parser.add_argument("-i", "--id", default=0, dest="id", type=int, help="Unique identifier for the sensor.")

    args = parser.parse_args()
    if args.id < 1 or args.id > settings.get("number_of_sensors"):
        print("Provide a non-negative and non-zero ID that is smaller or equal to the total number of sensors")
    else:
        sensor = XBee_Sensor(settings, args.id)
        sensor.run()

if __name__ == "__main__":
    main(sys.argv[1:])
