import sys
import time
import random
from __init__ import __package__
from core.Thread_Manager import Thread_Manager
from core.USB_Manager import USB_Manager
from settings import Arguments
from zigbee.XBee_Packet import XBee_Packet
from zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical

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
    usb_manager = USB_Manager()
    usb_manager.index()

    try:
        arguments = Arguments("settings.json", argv)
        xbee_sensor = XBee_Sensor_Physical(arguments, thread_manager,
                                           usb_manager, get_location,
                                           receive_packet, location_valid)

        arguments.check_help()

        xbee_sensor.activate()

        # Enqueue a custom packet.
        packet = XBee_Packet()
        packet.set("specification", "waypoint_add")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        packet.set("index", 22)
        packet.set("to_id", 2)
        xbee_sensor.enqueue(packet)
        time.sleep(1)

        # Start the signal strength measurements.
        xbee_sensor.start()

        while True:
            time.sleep(1)
    except:
        thread_manager.destroy()
        usb_manager.clear()

if __name__ == "__main__":
    main(sys.argv[1:])
