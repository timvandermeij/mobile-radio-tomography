import sys
import time
import random
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Packet import XBee_Packet
from zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical
from zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler

def get_location():
    """
    Get the current GPS location (latitude and longitude pair).
    """

    return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_physical")

    sensor_id = settings.get("id")
    scheduler = XBee_TDMA_Scheduler(sensor_id, arguments)
    location_callback = get_location
    sensor = XBee_Sensor_Physical(sensor_id, arguments, scheduler,
                                  location_callback)

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
