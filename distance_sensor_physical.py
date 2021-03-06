import sys
import time
import traceback
from __init__ import __package__
from settings import Arguments
from environment import Environment

def main(argv):
    arguments = Arguments("settings.json", argv)

    try:
        environment = Environment.setup(arguments, simulated=False)
        distance_sensors = environment.get_distance_sensors()
    except Exception:
        arguments.error(traceback.format_exc())

    settings = arguments.get_settings("distance_sensor_physical")

    arguments.check_help()

    while True:
        for sensor in distance_sensors:
            print("Measured distance: {} m".format(sensor.get_distance()))
        time.sleep(settings.get("interval_delay"))

if __name__ == "__main__":
    main(sys.argv[1:])
