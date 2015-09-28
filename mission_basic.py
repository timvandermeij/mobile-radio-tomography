"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import time
import math
from droneapi.lib import VehicleMode, Location, Command
from pymavlink import mavutil

# Package imports
from __init__ import __package__
from settings import Settings
from distance import Distance_Sensor_Simulator
from trajectory import Mission

# Main mission program
# TODO: Move more code into modules
def main():
    # Connect to API provider and get vehicle object
    api = local_connect()
    vehicle = api.get_vehicles()[0]
    mission_settings = Settings("settings.json", "mission")

    mission = Mission(api, vehicle, mission_settings)
    print("Clear the current mission")
    mission.clear_mission()

    print("Create a new mission")
    size = 50
    altitude = 10
    speed = 1.0
    num_commands = mission.add_square_mission(vehicle.location, altitude, size)
    print("{} commands in the mission!".format(num_commands))
    # Make sure that mission being sent is displayed on console cleanly
    time.sleep(2)

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff(altitude, speed)

    print("Starting mission")
    # Set mode to AUTO to start mission
    vehicle.mode = VehicleMode("AUTO")
    vehicle.flush()

    # Monitor mission
    # We can get and set the command number and use convenience function for 
    # finding distance to an object or the next waypoint.

    sensor = Distance_Sensor_Simulator(vehicle)
    # Margin in meters at which we are too close to an object
    closeness = mission_settings.get("closeness")
    # Distance in meters above which we are uninterested in objects
    farness = mission_settings.get("farness")
    # Seconds to wait before checking sensors and waypoints again
    loop_delay = mission_settings.get("loop_delay")

    while True:
        print("Velocity: {} m/s".format(vehicle.velocity))
        print("Altitude: {} m".format(vehicle.location.alt))
        sensor_distance = sensor.get_distance(vehicle.location)
        if sensor_distance < farness:
            print("Distance to object: {} m".format(sensor_distance))
            if sensor_distance < closeness:
                print("Too close to the object, halting.")
                vehicle.mode = VehicleMode("GUIDED")
                mission.set_speed(0)
                if sensor_distance == 0:
                    print("Inside the object, abort mission.")
                    sys.exit(1)
                else:
                    break

        nextwaypoint = vehicle.commands.next
        distance = mission.distance_to_current_waypoint()
        if nextwaypoint > 1:
            if distance < farness:
                print("Distance to waypoint ({}): {} m".format(nextwaypoint, distance))
                if distance < closeness:
                    print("Close enough: skip to next waypoint")
                    vehicle.commands.next = nextwaypoint + 1
                    nextwaypoint = nextwaypoint + 1

        if nextwaypoint >= num_commands:
            print("Exit 'standard' mission when heading for final waypoint ({})".format(num_commands))
            break

        time.sleep(loop_delay)

    print("Return to launch")
    vehicle.mode = VehicleMode("RTL")
    # Flush to ensure changes are sent to autopilot
    vehicle.flush()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file.
if __name__ in ["__main__", "__builtin__"]:
    main()
