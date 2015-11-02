import sys

from __init__ import __package__
from settings import Arguments
from geometry import Geometry
from trajectory.Environment import Environment_Simulator
from trajectory.MockVehicle import MockVehicle
from trajectory.Viewer import Viewer_Interactive

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("environment_viewer_interactive")

    geometry_class = settings.get("geometry_class")
    geometry = Geometry.__dict__[geometry_class]()

    vehicle = MockVehicle(geometry)
    environment = Environment_Simulator(vehicle, geometry, arguments)

    viewer = Viewer_Interactive(environment, settings)

    arguments.check_help()

    viewer.start()

if __name__ == "__main__":
    main(sys.argv[1:])
