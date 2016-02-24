"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Based on mission_basic.py in Dronekit, but supports other vehicle types as well.
Documentation for the source is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import traceback

# Package imports
# Ensure that we can import from the current directory as a package since 
# running a Python script directly does not define the correct package
from __init__ import __package__
from environment.Environment import Environment
from settings import Arguments
from trajectory import Mission
from trajectory.Monitor import Monitor

# Main mission program
class Setup(object):
    def __init__(self, arguments):
        self.arguments = arguments
        self.settings = self.arguments.get_settings("mission")

    def start(self):
        environment = Environment.setup(self.arguments)

        mission_class = self.settings.get("mission_class")
        mission = Mission.__dict__[mission_class](environment, self.settings)

        monitor = Monitor(mission, environment)

        self.arguments.check_help()

        print("Setting up mission")
        mission.setup()
        mission.display()

        # As of ArduCopter 3.3 it is possible to take off using a mission item.
        mission.arm_and_takeoff()
        mission.display()

        print("Starting mission")
        mission.start()

        # Monitor mission
        monitor.setup()

        try:
            if monitor.use_viewer():
                from trajectory.Viewer import Viewer_Vehicle
                viewer = Viewer_Vehicle(environment, monitor)
                viewer.start()
            else:
                ok = True
                while ok:
                    ok = monitor.step()
                    if ok:
                        monitor.sleep()
        except RuntimeError, e:
            print(e)
        except Exception, e:
            # Handle exceptions gracefully by attempting to stop the program 
            # ourselves. Unfortunately KeyboardInterrupts are not passed to us 
            # when we run under pymavlink.
            traceback.print_exc()

        monitor.stop()
        mission.return_to_launch()

def main(argv):
    arguments = Arguments("settings.json", argv)
    setup = Setup(arguments)
    setup.start()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file. Ensure MAVProxy arguments do not 
# conflict with our own arguments.
if __name__ == "__main__":
    main(sys.argv[1:])
elif __name__ == "__builtin__":
    main([])
