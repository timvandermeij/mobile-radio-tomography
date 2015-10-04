"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import time
import math
import traceback

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

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
from trajectory import Mission, Memory_Map, Environment
from trajectory.MockVehicle import MockAPI, MockVehicle
from geometry import Geometry

# TODO: Cleanup code, move more code into modules.
# Main mission program
def main():
    mission_settings = Settings("settings.json", "mission")

    try:
        geometry_class = mission_settings.get("geometry_class")
        geo = Geometry.__dict__[geometry_class]()
    except:
        geo = Geometry.Geometry_Spherical()

    if mission_settings.get("vehicle_simulation"):
        api = MockAPI()
        vehicle = MockVehicle(geo)
    else:
        # Connect to API provider and get vehicle object
        api = local_connect()
        vehicle = api.get_vehicles()[0]

    try:
        scenefile = mission_settings.get("scenefile")
    except KeyError:
        scenefile = None

    environment = Environment(vehicle, geo, scenefile)

    print("Setting up mission")
    mission = Mission(api, environment, mission_settings)
    mission.add_square_mission(self.vehicle.location)
    mission.display()

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff()

    print("Starting mission")
    # Set mode to AUTO to start mission
    vehicle.mode = VehicleMode("AUTO")
    vehicle.flush()

    # Monitor mission
    # We can get and set the command number and use convenience function for 
    # finding distance to an object or the next waypoint.

    try:
        angles = list(mission_settings.get("sensors"))
    except KeyError:
        angles = [0]

    sensors = [Distance_Sensor_Simulator(environment, angle) for angle in angles]
    colors = ["red", "purple", "black"]
    # Margin in meters at which we are too close to an object
    closeness = mission_settings.get("closeness")
    # Distance in meters above which we are uninterested in objects
    farness = mission_settings.get("farness")
    # Seconds to wait before checking sensors and waypoints again
    loop_delay = mission_settings.get("loop_delay")

    # Create a memory map for the vehicle to track where it has seen objects. 
    # This can later be used to find the target object or to fly around 
    # obstacles without colliding.
    memory_size = mission.get_space_size()
    memory_map = Memory_Map(environment, memory_size)

    # "Cheat" to see 2d map of collision data
    patches = []
    if scenefile is None:
        for obj in environment.objects:
            if isinstance(obj, tuple):
                polygon = Polygon([memory_map.get_xy_index(loc) for loc in obj])
                patches.append(polygon)
            elif 'center' in obj:
                idx = memory_map.get_xy_index(obj['center'])
                patches.append(Circle(idx, radius=obj['radius']))

    p = PatchCollection(patches, cmap=matplotlib.cm.jet, alpha=0.4)
    patch_colors = 50*np.ones(len(patches))
    p.set_array(np.array(patch_colors))
    fig, ax = plt.subplots()

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
            vehicle_idx = memory_map.get_index(environment.get_location())
            memory_map.set(vehicle_idx, -1)

            # Instead of performing an AUTO mission, we can also stand still 
            # and change the angle to look around. TODO: Make use of this when 
            # we're at a waypoint to look around? Make whole mission GUIDED?

            #vehicle.mode = VehicleMode("GUIDED")
            #mission.send_global_velocity(0,0,0)
            #vehicle.flush()
            #mission.set_yaw(yaw % 360, relative=False)
            #print("Velocity: {} m/s".format(vehicle.velocity))
            #print("Altitude: {} m".format(vehicle.location.alt))
            #print("Yaw: {} Expected: {}".format(vehicle.attitude.yaw*180/math.pi, yaw % 360))

            i = 0
            for sensor in sensors:
                sensor_distance = sensor.get_distance()

                # Decide on doing something with the measured distance. If 
                # we're too close, we should take action by stopping and going 
                # somewhere else.
                if sensor_distance == 0:
                    print("Inside the object, abort mission.")
                    sys.exit(1)
                elif sensor_distance < closeness:
                    vehicle.mode = VehicleMode("GUIDED")
                    mission.set_speed(0)
                    raise RuntimeError("Too close to the object, halting.")
                elif sensor_distance < farness:
                    # Display the edge of the simulated object that is 
                    # responsible for the measured distance, and consequently 
                    # the point itself. This should be the closest "wall" in 
                    # the angle's direction. This is again a "cheat" for 
                    # checking if walls get visualized correctly.
                    angle = sensor.get_angle()
                    memory_map.handle_sensor(sensor_distance, angle)
                    sensor.draw_current_edge(plt, memory_map, colors[i])

                    print("=== [!] Distance to object: {} m (angle {}) ===".format(sensor_distance, angle))

                i = i + 1

            # Display the current memory map interactively.
            ax.add_collection(p)
            plt.imshow(memory_map.get_map(), origin='lower')
            plt.draw()
            plt.cla()

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
            memory_map.set(vehicle_idx, 0)
    except Exception, e:
        # Handle exceptions gracefully by attempting to stop the program 
        # ourselves. Unfortunately KeyboardInterrupts are not passed to us when 
        # we run under pymavlink.
        traceback.print_exc()
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
