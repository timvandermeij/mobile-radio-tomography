import sys
import time
import random
from __init__ import __package__
from core.Thread_Manager import Thread_Manager
from settings import Arguments
from zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

def get_location():
    return (random.randint(0, 5), random.randint(0, 5))

def receive_packet(packet):
    pass

def location_valid(other_valid=None):
    return True

def main(argv):
    thread_manager = Thread_Manager()

    try:
        arguments = Arguments("settings.json", argv)
        xbee_sensor = XBee_Sensor_Simulator(arguments, thread_manager, None,
                                            get_location, receive_packet,
                                            location_valid)

        arguments.check_help()

        xbee_sensor.activate()
        xbee_sensor.start()

        while True:
            time.sleep(1)
    except:
        thread_manager.destroy()

if __name__ == "__main__":
    main(sys.argv[1:])
