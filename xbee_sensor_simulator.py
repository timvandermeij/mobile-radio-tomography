import sys
import time
import random
from __init__ import __package__
from core.Thread_Manager import Thread_Manager
from settings import Arguments
from zigbee.XBee_Packet import XBee_Packet
from zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

def get_location():
    """
    Get the current GPS location (latitude and longitude pair).
    """

    return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

def receive_packet(packet):
    """
    Handle a custom packet that has been sent to this sensor.
    """

    print("> Custom packet received: {}".format(packet.get_all()))

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

        timestamp = 0
        while True:
            # Enqueue a custom packet at a fixed interval.
            if xbee_sensor._id > 0 and time.time() > timestamp:
                timestamp = time.time() + 8
                packet = XBee_Packet()
                packet.set("specification", "memory_map_chunk")
                packet.set("latitude", 123456789.12)
                packet.set("longitude", 123495678.34)
                xbee_sensor.enqueue(packet)

            time.sleep(1)
    except:
        thread_manager.destroy()

if __name__ == "__main__":
    main(sys.argv[1:])
