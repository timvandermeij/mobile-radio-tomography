import sys

from __init__ import __package__
from settings import Arguments
from environment import Environment
from trajectory.Viewer import Viewer_Interactive

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("environment_viewer_interactive")

    environment = Environment.setup(arguments)
    viewer = Viewer_Interactive(environment, settings)

    arguments.check_help()

    viewer.start()

if __name__ == "__main__":
    main(sys.argv[1:])
