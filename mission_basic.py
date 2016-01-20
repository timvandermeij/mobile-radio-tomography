"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import traceback
import time

import dronekit

# Package imports
# Ensure that we can import from the current directory as a package since 
# running a python script directly does not define the correct package
from __init__ import __package__
from settings import Arguments
from trajectory import Mission
from trajectory.MockVehicle import MockVehicle
from trajectory.Monitor import Monitor
from geometry import Geometry

# Main mission program
class Setup(object):
    def __init__(self, arguments):
        self.arguments = arguments
        self.settings = self.arguments.get_settings("mission")

        geometry_class = self.settings.get("geometry_class")
        self.geometry = Geometry.__dict__[geometry_class]()

    def start(self):
        connect = self.settings.get("connect")
        if connect == "":
            # Not connecting to a vehicle means we use our own simulation
            self.vehicle = MockVehicle(self.geometry)
        else:
            # We're running via builtins execfile or some other module, so 
            # assume we use ArduPilot simulation/actual MAVProxy link to the 
            # vehicle's flight controller.
            if not isinstance(self.geometry, Geometry.Geometry_Spherical):
                raise ValueError("Dronekit only works with spherical geometry")

            # Connect to the vehicle autopilot to get the vehicle API object
            self.vehicle = dronekit.connect(connect, baud=self.settings.get("mavlink_baud_rate"))

            # Wait until location has been filled
            if self.settings.get("gps"):
                self.wait = True
                self.vehicle.add_attribute_listener('location.global_relative_frame', self.listen)

                while self.wait:
                    time.sleep(1.0)
                    print('Waiting for location update...')

        simulation = self.settings.get("vehicle_simulation")
        if not simulation and isinstance(self.vehicle, MockVehicle):
            print("Warning: Using mock vehicle while not in simulation. This may be useful for testing the distance sensor but might indicate an incorrect setting in other cases.")

        if simulation:
            from environment.Environment_Simulator import Environment_Simulator
            environment = Environment_Simulator(self.vehicle, self.geometry, self.arguments)
        else:
            from environment.Environment_Physical import Environment_Physical
            environment = Environment_Physical(self.vehicle, self.geometry, self.arguments)

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

    def listen(self, vehicle, attr_name, value):
        vehicle.remove_attribute_listener('location.global_relative_frame', self.listen)
        self.wait = False

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
