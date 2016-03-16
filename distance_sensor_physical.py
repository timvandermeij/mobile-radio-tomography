import sys
import time
from __init__ import __package__
from settings import Arguments
from environment import Environment

def main(argv):
    arguments = Arguments("settings.json", argv)

    environment = Environment.setup(arguments, simulated=False)
    distance_sensors = environment.get_distance_sensors()
    settings = arguments.get_settings("distance_sensor_physical")

    while True:
        for sensor in distance_sensors:
            print("Measured distance: {} m".format(sensor.get_distance()))
        time.sleep(settings.get("interval_delay"))

if __name__ == "__main__":
    main(sys.argv[1:])
