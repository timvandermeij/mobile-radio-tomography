"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import traceback

# Package imports
# Ensure that we can import from the current directory as a package since 
# running this via pymavproxy makes it not have this in the path, and running 
# scripts in general does not define the correct package
sys.path.insert(0, os.getcwd())
from __init__ import __package__
from settings import Arguments
from trajectory import Mission
from trajectory.MockVehicle import MockAPI, MockVehicle
from trajectory.Monitor import Monitor
from geometry import Geometry

# Main mission program
def main(argv):
    arguments = Arguments("settings.json", argv)
    mission_settings = arguments.get_settings("mission")

    geometry_class = mission_settings.get("geometry_class")
    geometry = Geometry.__dict__[geometry_class]()

    simulation = mission_settings.get("vehicle_simulation")
    if __name__ == "__main__":
        # Directly running the file means we use our own simulation
        if not simulation:
            print("Warning: Using mock vehicle while not in simulation. This may be useful for testing the distance sensor but might indicate an incorrect setting in other cases.")

        api = MockAPI()
        vehicle = MockVehicle(geometry)
    else:
        # We're running via builtins execfile or some other module, so assume 
        # we use ArduPilot simulation/actual MAVProxy link to the vehicle's 
        # flight controller.
        if not isinstance(geometry, Geometry.Geometry_Spherical):
            raise ValueError("Dronekit only works with spherical geometry")

        # Connect to API provider and get vehicle object
        api = local_connect()
        vehicle = api.get_vehicles()[0]

    if simulation:
        from environment.Environment_Simulator import Environment_Simulator
        environment = Environment_Simulator(vehicle, geometry, arguments)
    else:
        from environment.Environment_Physical import Environment_Physical
        environment = Environment_Physical(vehicle, geometry, arguments)

    mission_class = mission_settings.get("mission_class")
    mission = Mission.__dict__[mission_class](api, environment, mission_settings)

    monitor = Monitor(api, mission, environment)

    arguments.check_help()

    print("Setting up mission")
    mission.setup()
    mission.display()

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff()

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
        # ourselves. Unfortunately KeyboardInterrupts are not passed to us when 
        # we run under pymavlink.
        traceback.print_exc()

    monitor.stop()
    mission.return_to_launch()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file. Ensure MAVProxy arguments do not 
# conflict with our own arguments.
if __name__ == "__main__":
    main(sys.argv[1:])
elif __name__ == "__builtin__":
    main([])
