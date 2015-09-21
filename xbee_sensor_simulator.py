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
UDP_NETWORK_SWEEP_DELAY = 1 # seconds
UDP_NETWORK_LOOP_DELAY = 0.05 # seconds

class TDMA_Scheduler(object):
    def __init__(self, id):
        self.id = id
        self.last_timestamp = 0

    def get_next_timestamp(self):
        # Get the next timestamp for starting transmission of packets.
        if self.last_timestamp == 0:
            self.last_timestamp = time.time() + ((self.id / UDP_NETWORK_TOTAL_NODES) *
                                  UDP_NETWORK_SWEEP_DELAY)
        else: 
            self.last_timestamp += UDP_NETWORK_SWEEP_DELAY
        
        return self.last_timestamp

class Xbee_Sensor_Simulator(object):
    def __init__(self, id):
        # Initialize the sensor with its ID and a unique, non-blocking UDP socket.
        self.id = id
        self.scheduler = TDMA_Scheduler(self.id)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((UDP_NETWORK_IP, UDP_NETWORK_PORT + self.id))
        self.socket.setblocking(0)

    def run(self):
        # Execute the sensor's main loop that constantly sends and receives packets.
        next_timestamp = self.scheduler.get_next_timestamp()
        while True:
            # Add a small delay to avoid 100% CPU usage due to the while loop
            time.sleep(UDP_NETWORK_LOOP_DELAY)

            if time.time() >= next_timestamp:
                self._send()
                next_timestamp = self.scheduler.get_next_timestamp()

            self._receive()

    def _send(self):
        # Send packets to all other sensors
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

    def _receive(self):
        # Receive packets from all other sensors
        try:
            packet = self.socket.recv(UDP_NETWORK_BUFFER_SIZE)
            print(json.loads(packet))
        except socket.error:
            pass

def main(argv):
    parser = argparse.ArgumentParser(description="Simulate packet communication in a WiFi sensor network.")
    parser.add_argument("-i", "--id", default=0, dest="id", type=int, help="Unique identifier for the sensor.")

    args = parser.parse_args()
    if args.id < 1 or args.id > UDP_NETWORK_TOTAL_NODES:
        print("Provide a non-negative and non-zero ID that is smaller or equal to the total number of sensors")
    else:
        sensor = Xbee_Sensor_Simulator(args.id)
        sensor.run()

if __name__ == "__main__":
    main(sys.argv[1:])
