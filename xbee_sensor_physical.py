import sys
import time
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical
from zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_physical")

    sensors = []
    for sensor_id in range(1, settings.get("number_of_sensors") + 1):
        scheduler = XBee_TDMA_Scheduler(sensor_id, arguments)
        sensor = XBee_Sensor_Physical(sensor_id, arguments, scheduler)
        sensors.append(sensor)

    arguments.check_help()

    while True:
        try:
            for sensor in sensors:
                sensor.activate()

            time.sleep(settings.get("loop_delay"))
        except KeyboardInterrupt:
            for sensor in sensors:
                sensor.deactivate()

            break

if __name__ == "__main__":
    main(sys.argv[1:])
