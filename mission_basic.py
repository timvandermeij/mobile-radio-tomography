"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from droneapi.lib import VehicleMode, Location, Command
from pymavlink import mavutil

# Package imports
# Ensure that we can import from the current directory as a package since 
# running this via pymavproxy makes it not have this in the path, and running 
# scripts in general does not define the correct package
sys.path.insert(0, os.getcwd())
from __init__ import __package__
from settings import Settings
from distance.Distance_Sensor_Simulator import Distance_Sensor_Simulator
from trajectory import Mission

# TODO: Cleanup code, move more code into modules.
from utils.Geometry import *

def get_index(bl, tr, memory_size, loc):
    """
    Convert location coordinates to indices for a two-dimensional matrix.
    The `bl` and `tr` are the first and last points that fit in the matrix in both dimensions, respectively. The `memory_size` is the number of entries per dimension.
    """
    dlat = tr.lat - bl.lat
    dlon = tr.lon - bl.lon
    y = ((loc.lat - bl.lat) / dlat) * memory_size
    x = ((loc.lon - bl.lon) / dlon) * memory_size
    return (x,y)

# Main mission program
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
    altitude = mission_settings.get("altitude")
    speed = mission_settings.get("speed")
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

    # Create a memory map for the vehicle to track where it has seen objects. 
    # This can later be used to find the target object or to fly around 
    # obstacles without colliding.
    memory_size = size*4
    memory_map = np.zeros((memory_size,memory_size))
    bl = get_location_meters(vehicle.location, -size*2, -size*2)
    tr = get_location_meters(vehicle.location, size*2, size*2)
    # Temporary "cheat" to see 2d map of collision data
    for i in xrange(0,memory_size):
        for j in xrange(0,memory_size):
            loc = get_location_meters(bl, i, j)
            if sensor.get_distance(loc) == 0:
                memory_map[i,j] = 0.5

    # Set up interactive drawing of the memory map. This makes the 
    # dronekit/mavproxy fairly annoyed since it creates additional 
    # threads/windows. One might have to press Ctrl-C and normal keys to make 
    # the program stop.
    plt.gca().set_aspect("equal", adjustable="box")
    plt.ion()
    plt.show()

    yaw = 0
    arrow = None
    try:
        while not api.exit:
            # Put our current location on the map for visualization. Of course, 
            # this location is also "safe" since we are flying there.
            x,y = get_index(bl, tr, memory_size, vehicle.location)
            print(x,y)
            memory_map[y,x] = -1

            # Instead of performing an AUTO mission, we can also stand still 
            # and change the angle to look around. TODO: Make use of this when 
            # we're at a waypoint to look around? Make whole mission GUIDED?

            #mission.send_global_velocity(0,0,0)
            #vehicle.flush()
            #mission.set_yaw(yaw % 360, relative=False)
            #print("Velocity: {} m/s".format(vehicle.velocity))
            #print("Altitude: {} m".format(vehicle.location.alt))

            angle = bearing_to_angle(vehicle.attitude.yaw)
            #print("Yaw: {} Expected: {} Angle: {}".format(vehicle.attitude.yaw*180/math.pi, yaw, angle*180/math.pi))

            sensor_distance = sensor.get_distance(vehicle.location)
            if sensor_distance < farness:
                # Estimate the location of the point based on the distance from 
                # the distance sensor as well as our own angle.
                dy = math.sin(angle) * sensor_distance
                dx = math.cos(angle) * sensor_distance
                loc = get_location_meters(vehicle.location, dy, dx)

                print("Estimated location: {}, {}".format(loc.lat, loc.lon))

                # Convert point location to indices in the memory map.
                x2,y2 = get_index(bl, tr, memory_size, loc)
                print("Point in map: {},{}".format(y2,x2))
                if 0 < y2 < memory_size and 0 < x2 < memory_size:
                    # Point is within the (closed-space) memory map, so we can 
                    # track it.
                    memory_map[y2,x2] = 1

                # Display the edge of the simulated object that is responsible 
                # for the measured distance, and consequently the point itself. 
                # This should be the closest "wall" in the angle's direction. 
                # This is again a "cheat" for checking if walls get visualized 
                # correctly.
                if arrow is not None:
                    arrow.remove()
                    arrow = None
                if sensor.current_edge is not None:
                    options = {
                        "arrowstyle": "<-, head_width=1, head_length=1",
                        "color": "red",
                        "linewidth": 2
                    }
                    e0 = get_index(bl, tr, memory_size, sensor.current_edge[0])
                    e1 = get_index(bl, tr, memory_size, sensor.current_edge[1])
                    print("Relevant edges: {},{}".format(e0, e1))
                    arrow = plt.annotate("", e0, e1, arrowprops=options)

                # Now actually decide on doing something with the measured 
                # distance. If we're too close, we should take action by 
                # stopping and going somewhere else.
                print("=== [!] Distance to object: {} m ===".format(sensor_distance))
                if sensor_distance < closeness:
                    print("Too close to the object, halting.")
                    vehicle.mode = VehicleMode("GUIDED")
                    mission.set_speed(0)
                    if sensor_distance == 0:
                        print("Inside the object, abort mission.")
                        sys.exit(1)
                    else:
                        break

            # Display the current memory map interactively.
            plt.imshow(memory_map, origin='lower')
            plt.draw()

            # Handle waypoint locations in our mission.
            # If we are close to the next waypoint, then we can start doing 
            # other things.
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

            # When we're standing still, we can rotate the vehicle to measure 
            # distances to objects.
            yaw = yaw + 10

            # Remove the vehicle from the current location. We set it to "safe" 
            # since there is no object here.
            memory_map[y,x] = 0
    except Exception, e:
        # Handle exceptions gracefully by attempting to stop the program 
        # ourselves. Unfortunately KeyboardInterrupts are not passed to us when 
        # we run under pymavlink.
        print("Exception: {}".format(e))
        plt.close()

    print("Return to launch")
    vehicle.mode = VehicleMode("RTL")
    # Flush to ensure changes are sent to autopilot
    vehicle.flush()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file.
if __name__ in ["__main__", "__builtin__"]:
    main()
