import importlib
import sys
import time
from __init__ import __package__
from settings import Arguments
from location.Line_Follower import Line_Follower_Direction

def callback():
    pass

def main(argv):
    location = (0, 0)
    direction = Line_Follower_Direction.UP
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("line_follower_base")
    # Line follower class to use in the line follower runner.
    line_follower_module = settings.get("line_follower_module")
    module = importlib.import_module("{}.location.{}".format(__package__, line_follower_module))
    line_follower_class = module.__dict__[line_follower_module]

    line_follower = line_follower_class(location, direction, callback, arguments)

    while True:
        line_follower.activate()
        print(line_follower.read())
        line_follower.deactivate()
        time.sleep(1)

if __name__ == "__main__":
    main(sys.argv[1:])
