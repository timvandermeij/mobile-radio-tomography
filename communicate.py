import sys
import time
import json
import argparse
from random import randint
from multiprocessing.connection import Listener, Client, AuthenticationError

NETWORK_IP = "127.0.0.1"
NETWORK_PORT = 3233
NETWORK_KEY = "855aa35dc939fa09c1dd8d7e6b95a3"
NETWORK_SEND_LIMIT = 10

class Sensor(object):
    def run(self):
        raise NotImplementedError("Subclasses must override run()")

    def quit(self):
        raise NotImplementedError("Subclasses must override quit()")

class Receiver(Sensor):
    def __init__(self):
        # Initialize the receiver with a connection to the socket.
        self.listener = Listener((NETWORK_IP, NETWORK_PORT), authkey=NETWORK_KEY)
        try:
            self.connection = self.listener.accept()
        except AuthenticationError:
            print("Network authentication failed.")
            self.listener.close()
            sys.exit()

    def run(self):
        # Listen for incoming packets on the socket.
        while True:
            try:
                packet = self.connection.recv()
                print(json.loads(packet))
            except EOFError:
                print("No processes are sending packets anymore.")
                break

    def quit(self):
        # Stop receiving packets and exit.
        self.connection.close()
        self.listener.close()
        sys.exit()

class Sender(Sensor):
    def __init__(self, id):
        self.id = id
        try:
            self.connection = Client((NETWORK_IP, NETWORK_PORT), authkey=NETWORK_KEY)
        except AuthenticationError:
            print("Network authentication failed.")
            sys.exit()

    def run(self):
        # Send a packet over the socket every second.
        count = 0
        while True:
            time.sleep(1)
            packet = {
                "from": self.id,
                "rssi": -randint(1,60)
            }
            self.connection.send(json.dumps(packet))
            count += 1
            if count == NETWORK_SEND_LIMIT:
                break

    def quit(self):
        # Stop receiving packets and exit.
        self.connection.close()
        sys.exit()

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
    sensor.quit()

if __name__ == "__main__":
    main(sys.argv[1:])
