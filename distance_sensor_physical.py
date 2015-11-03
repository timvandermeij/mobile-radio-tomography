import sys
import time
from __init__ import __package__
from settings import Arguments
from distance.Distance_Sensor_Physical import Distance_Sensor_Physical
from geometry.Geometry import Geometry
from trajectory.Environment import Environment_Simulator
from trajectory.MockVehicle import MockVehicle

def main(argv):
    arguments = Arguments("settings.json", argv)

    environment = Environment.setup(arguments)
    distance_sensor = Distance_Sensor_Physical(environment)
    settings = arguments.get_settings("distance_sensor_physical")

    while True:
        print("Measured distance: {} m".format(distance_sensor.get_distance()))
        time.sleep(settings.get("interval_delay"))

if __name__ == "__main__":
    main(sys.argv[1:])
