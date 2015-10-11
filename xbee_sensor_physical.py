import sys
import time
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical
from zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_physical")

    sensor_id = settings.get("id")
    scheduler = XBee_TDMA_Scheduler(sensor_id, arguments)
    sensor = XBee_Sensor_Physical(sensor_id, arguments, scheduler)

    arguments.check_help()

    while True:
        try:
            sensor.activate()
            time.sleep(settings.get("loop_delay"))
        except KeyboardInterrupt:
            sensor.deactivate()
            break

if __name__ == "__main__":
    main(sys.argv[1:])
