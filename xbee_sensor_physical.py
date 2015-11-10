import sys
import time
import random
from __init__ import __package__
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

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_physical")

    sensor = XBee_Sensor_Physical(arguments, get_location, receive_packet)

    arguments.check_help()

    timestamp = 0
    while True:
        try:
            # Enqueue a custom packet at a fixed interval.
            if sensor.id > 0 and time.time() > timestamp:
                timestamp = time.time() + 8
                packet = XBee_Packet()
                packet.set("specification", "memory_map_chunk")
                packet.set("latitude", 123456789.12)
                packet.set("longitude", 123495678.34)
                sensor.enqueue(packet)

            sensor.activate()
            time.sleep(settings.get("loop_delay"))
        except KeyboardInterrupt:
            sensor.deactivate()
            break

if __name__ == "__main__":
    main(sys.argv[1:])
