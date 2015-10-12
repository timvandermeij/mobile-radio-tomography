import sys

from __init__ import __package__
from settings import Arguments
from geometry.Geometry import Geometry
from trajectory import Environment_Simulator
from trajectory.MockVehicle import MockVehicle
from trajectory.Viewer import Viewer_Interactive

def main(argv):
    arguments = Arguments("settings.json", argv)
    geometry = Geometry()
    vehicle = MockVehicle(geometry)
    environment = Environment_Simulator(vehicle, geometry, arguments)

    viewer = Viewer_Interactive(environment)

    arguments.check_help()

    viewer.start()

if __name__ == "__main__":
    main(sys.argv[1:])
