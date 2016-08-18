"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Based on mission_basic.py in Dronekit, but supports other vehicle types as well.
Documentation for the source is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import traceback

# Package imports
# Ensure that we can import from the current directory as a package since 
# running a Python script directly does not define the correct package
from __init__ import __package__
from environment.Environment import Environment
from mission.Mission import Mission
from settings import Arguments
from trajectory.Monitor import Monitor

# Main mission program
class Setup(object):
    def __init__(self, arguments):
        self.arguments = arguments
        self.activated = False

        self.environment = None
        self.mission = None
        self.monitor = None

    def setup(self):
        try:
            self.environment = Environment.setup(self.arguments)

            self.mission = Mission.create(self.environment, self.arguments)

            self.monitor = Monitor(self.mission, self.environment)
        except Exception:
            self.arguments.error(traceback.format_exc())

        self.arguments.check_help()

        infrared_sensor = self.environment.get_infrared_sensor()
        if infrared_sensor is not None:
            infrared_sensor.register("start", self.enable)
            infrared_sensor.register("pause", self.monitor.pause)
            infrared_sensor.register("stop", self._infrared_disable)
            infrared_sensor.activate()
        else:
            self.activated = True

        print("Setting up mission")
        self.mission.setup()
        self.mission.display()

        self.monitor.setup()

        # Arm the vehicle and take off to the specified altitude if the vehicle 
        # can fly.
        self.mission.arm_and_takeoff()
        self.mission.display()

        while not self.activated:
            self.monitor.sleep()

        self.start()

    def enable(self):
        self.activated = True

    def start(self):
        print("Starting mission")
        self.monitor.start()

        # Monitor mission
        try:
            if self.monitor.use_viewer():
                from trajectory.Viewer import Viewer_Vehicle
                viewer = Viewer_Vehicle(self.environment, self.monitor)
                viewer.start()
            else:
                ok = True
                while ok and self.activated:
                    ok = self.monitor.step()
                    if ok:
                        self.monitor.sleep()
        except RuntimeError as e:
            # Handle runtime errors from the monitor loop as informative and 
            # loggable errors, but allow the vehicle to attempt to return to 
            # launch.
            print(e)
            self.environment.thread_manager.log("main thread")

        # Return to lauch at the end of the mission or when we can safely 
        # return before a potential problem.
        if self.activated:
            self.monitor.stop()
            self.mission.return_to_launch()

    def disable(self):
        if self.activated:
            self.activated = False
            print("Stopped mission")

        try:
            if self.monitor:
                self.monitor.stop()

            if self.environment:
                self.environment.thread_manager.destroy()
                self.environment.usb_manager.clear()
        except:
            traceback.print_exc()
            sys.exit(1)

    def _infrared_disable(self):
        self.environment.thread_manager.interrupt("infrared_sensor")

def main(argv):
    arguments = Arguments("settings.json", argv)
    setup = Setup(arguments)
    try:
        setup.setup()
    except Exception:
        traceback.print_exc()
    finally:
        setup.disable()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file. Ensure MAVProxy arguments do not 
# conflict with our own arguments.
if __name__ == "__main__":
    main(sys.argv[1:])
elif __name__ == "__builtin__":
    main([])
