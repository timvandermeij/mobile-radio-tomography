import sys
import time
import random
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Packet import XBee_Packet
from zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical
from zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler

def location_callback():
    """
    Get the current GPS location (latitude and longitude pair).
    """

    return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

def receive_callback(packet):
    """
    Handle a custom packet that has been sent to this sensor.
    """

    print("> Custom packet received: {}".format(packet.serialize()))

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_physical")
    default_sensor_id = 0

    scheduler = XBee_TDMA_Scheduler(default_sensor_id, arguments)
    sensor = XBee_Sensor_Physical(arguments, scheduler, location_callback,
                                  receive_callback)

    arguments.check_help()

    timestamp = 0
    while True:
        try:
            # Enqueue a custom packet at a fixed interval.
            if sensor.id > 0 and time.time() > timestamp:
                timestamp = time.time() + 8
                packet = XBee_Packet()
                packet.set("command", "continue")
                sensor.enqueue(packet)

            sensor.activate()
            time.sleep(settings.get("loop_delay"))
        except KeyboardInterrupt:
            sensor.deactivate()
            break

if __name__ == "__main__":
    main(sys.argv[1:])
