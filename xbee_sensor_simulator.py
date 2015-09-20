import sys
import time
import json
import argparse
from random import randint
import socket

UDP_NETWORK_IP = "127.0.0.1"
UDP_NETWORK_PORT = 3233
UDP_NETWORK_BUFFER_SIZE = 1024
UDP_NETWORK_TOTAL_NODES = 2
UDP_NETWORK_SEND_INTERVAL = 2
UDP_NETWORK_INTERVAL_DELAY = 0.05

class Xbee_Sensor_Simulator(object):
    def __init__(self, id):
        # Initialize the sensor with its ID and a unique, non-blocking UDP socket.
        self.id = id
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((UDP_NETWORK_IP, UDP_NETWORK_PORT + self.id))
        self.socket.setblocking(0)

    def run(self):
        # Execute the sensor's main loop that constantly sends and receives packets.
        last_send_timestamp = 0
        while True:
            # Add a small delay to avoid 100% CPU usage due to the while loop
            time.sleep(UDP_NETWORK_INTERVAL_DELAY)

            if time.time() - last_send_timestamp >= UDP_NETWORK_SEND_INTERVAL:
                self._send()
                last_send_timestamp = time.time()

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
