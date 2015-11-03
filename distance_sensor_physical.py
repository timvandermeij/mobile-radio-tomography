import sys
import time
from __init__ import __package__
from settings import Arguments
from distance.Distance_Sensor_Physical import Distance_Sensor_Physical
from geometry.Geometry import Geometry
from environment import Environment
from trajectory.MockVehicle import MockVehicle

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
