import sys
import time
import json
import argparse
from random import randint
import socket

UDP_NETWORK_IP = "127.0.0.1"
UDP_NETWORK_PORT = 3233
UDP_NETWORK_BUFFER_SIZE = 1024 # bytes
UDP_NETWORK_TOTAL_NODES = 3
UDP_NETWORK_SWEEP_DELAY = 6 # seconds
UDP_NETWORK_LOOP_DELAY = 0.05 # seconds

class TDMA_Scheduler(object):
    def __init__(self, id):
        self.id = id
        self.timestamp = 0

    def get_next_timestamp(self):
        # Get the next timestamp for starting transmission of packets.
        if self.timestamp == 0:
            self.timestamp = time.time() + ((self.id / UDP_NETWORK_TOTAL_NODES) *
                             UDP_NETWORK_SWEEP_DELAY)
        else: 
            self.timestamp += UDP_NETWORK_SWEEP_DELAY
        
        return self.timestamp

    def synchronize(self, packet):
        # Synchronize the scheduler after receiving a packet from
        # another sensor in the network. The transmission timestamp of this
        # sensor is the received transmission timestamp plus the number of
        # slots inbetween that sensor and this sensor.
        slot_time = UDP_NETWORK_SWEEP_DELAY / UDP_NETWORK_TOTAL_NODES
        from_sensor = int(packet["from"])
        timestamp = float(packet["timestamp"])
        if from_sensor < self.id:
            self.timestamp = timestamp + ((self.id - from_sensor) * slot_time)
        else:
            # Calculate how much time remains to complete the current round.
            completed_round = (UDP_NETWORK_TOTAL_NODES - from_sensor + 1) * slot_time
            self.timestamp = timestamp + completed_round + ((self.id - 1) * slot_time)

        return self.timestamp

class XBee_Sensor(object):
    def __init__(self, id):
        # Initialize the sensor with its ID and a unique, non-blocking UDP socket.
        self.id = id
        self.next_timestamp = 0
        self.scheduler = TDMA_Scheduler(self.id)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((UDP_NETWORK_IP, UDP_NETWORK_PORT + self.id))
        self.socket.setblocking(0)

    def run(self):
        # Execute the sensor's main loop that constantly sends and receives packets.
        self.next_timestamp = self.scheduler.get_next_timestamp()
        while True:
            # Add a small delay to avoid 100% CPU usage due to the while loop.
            time.sleep(UDP_NETWORK_LOOP_DELAY)

            if time.time() >= self.next_timestamp:
                self._send()
                self.next_timestamp = self.scheduler.get_next_timestamp()

            self._receive()

    def _send(self):
        # Send packets to all other sensors.
        for i in range(1, UDP_NETWORK_TOTAL_NODES + 1):
            if i == self.id:
                continue

            packet = {
                "from": self.id,
                "to": i,
                "timestamp": time.time(),
                "rssi": -randint(1,60)
            }
            self.socket.sendto(json.dumps(packet), (UDP_NETWORK_IP, UDP_NETWORK_PORT + i))
            print("-> {} sending at {}...".format(self.id, packet["timestamp"]))

    def _receive(self):
        # Receive packets from all other sensors.
        try:
            packet = json.loads(self.socket.recv(UDP_NETWORK_BUFFER_SIZE))
            self.next_timestamp = self.scheduler.synchronize(packet)
            print("{} receiving at {}...".format(self.id, time.time()))
        except socket.error:
            pass

def main(argv):
    parser = argparse.ArgumentParser(description="Simulate packet communication in a WiFi sensor network.")
    parser.add_argument("-i", "--id", default=0, dest="id", type=int, help="Unique identifier for the sensor.")

    args = parser.parse_args()
    if args.id < 1 or args.id > UDP_NETWORK_TOTAL_NODES:
        print("Provide a non-negative and non-zero ID that is smaller or equal to the total number of sensors")
    else:
        sensor = XBee_Sensor(args.id)
        sensor.run()

if __name__ == "__main__":
    main(sys.argv[1:])
