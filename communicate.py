import sys
import time
import json
import argparse
from random import randint
import socket

UDP_NETWORK_IP = "127.0.0.1"
UDP_NETWORK_PORT = 3233
UDP_NETWORK_BUFFER_SIZE = 1024
UDP_NETWORK_SEND_LIMIT = 50

class Sensor(object):
    def run(self):
        raise NotImplementedError("Subclasses must override run()")

class Receiver(Sensor):
    def __init__(self):
        # Initialize the receiver with a connection to a UDP socket.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((UDP_NETWORK_IP, UDP_NETWORK_PORT))

    def run(self):
        # Listen for incoming packets on the socket.
        while True:
            packet, address = self.socket.recvfrom(UDP_NETWORK_BUFFER_SIZE)
            print(json.loads(packet))

class Sender(Sensor):
    def __init__(self, id):
        # Initialize the sender with a connection to a UDP socket and an ID.
        self.id = id
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def run(self):
        # Send a packet over the socket every second.
        count = 0
        while True:
            time.sleep(1)
            packet = {
                "from": self.id,
                "rssi": -randint(1,60)
            }
            self.socket.sendto(json.dumps(packet), (UDP_NETWORK_IP, UDP_NETWORK_PORT))
            count += 1
            if count == UDP_NETWORK_SEND_LIMIT:
                break

def main(argv):
    parser = argparse.ArgumentParser(description="Simulate packet communication in a WiFi sensor network.")
    parser.add_argument("-s", "--sender", default=False, dest="sender",
                        action="store_true", help="Make this process a packet sender in the network.")
    parser.add_argument("-r", "--receiver", default=False, dest="receiver",
                        action="store_true", help="Make this process a packet sender in the network.")
    parser.add_argument("-i", "--id", default=randint(1,100), dest="id", type=int,
                        help="Unique identifier for a packet sender.")

    args = parser.parse_args()
    if not args.sender and not args.receiver:
        print("Provide a valid sensor type (sender or receiver).")
        sys.exit()
    elif args.sender and args.receiver:
        print("Provide only one valid sensor type (sender or receiver).")
        sys.exit()

    if args.sender:
        sensor = Sender(args.id)
    elif args.receiver:
        sensor = Receiver()

    sensor.run()

if __name__ == "__main__":
    main(sys.argv[1:])
