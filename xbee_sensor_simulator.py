import sys
import time
import random
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Packet import XBee_Packet
from zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator
from zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from zigbee.XBee_Viewer import XBee_Viewer

def get_location():
    """
    Get the current GPS location (latitude and longitude pair).
    """

    return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_simulator")

    viewer = XBee_Viewer(arguments)

    sensors = []
    for sensor_id in range(settings.get("number_of_sensors") + 1):
        scheduler = XBee_TDMA_Scheduler(sensor_id, arguments)
        location_callback = get_location
        sensor = XBee_Sensor_Simulator(sensor_id, arguments, scheduler,
                                       viewer, location_callback)
        sensors.append(sensor)

    arguments.check_help()
    viewer.draw_points()

    timestamp = 0
    while True:
        try:
            for sensor in sensors:
                # Enqueue a custom packet at a fixed interval.
                if sensor.id > 0 and time.time() > timestamp:
                    timestamp = time.time() + 5
                    packet = XBee_Packet()
                    packet.set("to_id", sensor.id % 2 + 1)
                    packet.set("command", "continue")
                    sensor.enqueue(packet)

                sensor.activate()

            time.sleep(settings.get("loop_delay"))
        except KeyboardInterrupt:
            for sensor in sensors:
                sensor.deactivate()

            break

if __name__ == "__main__":
    main(sys.argv[1:])
