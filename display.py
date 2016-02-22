import sys

from __init__ import __package__
from settings import Arguments
from geometry import Geometry
from environment import Environment
from trajectory.Viewer import Viewer_Interactive
from vehicle.Mock_Vehicle import Mock_Vehicle

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("environment_viewer_interactive")

    environment = Environment.setup(arguments, settings.get("geometry_class"))
    viewer = Viewer_Interactive(environment, settings)

    arguments.check_help()

    viewer.start()

if __name__ == "__main__":
    main(sys.argv[1:])
