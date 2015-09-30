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

class Memory_Map(object):
    def __init__(self, vehicle, memory_size):
        self.vehicle = vehicle
        self.size = memory_size
        self.map = np.zeros((self.size, self.size))
        # The `bl` and `tr` are the first and last points that fit in the 
        # matrix in both dimensions, respectively. The `memory_size` is the 
        # number of entries per dimension.
        self.bl = get_location_meters(vehicle.location, -self.size/2, -self.size/2)
        self.tr = get_location_meters(vehicle.location, self.size/2, self.size/2)

    def get_index(self, loc):
        """
        Convert location coordinates to indices for a two-dimensional matrix.
        """
        dlat = self.tr.lat - self.bl.lat
        dlon = self.tr.lon - self.bl.lon
        y = ((loc.lat - self.bl.lat) / dlat) * self.size
        x = ((loc.lon - self.bl.lon) / dlon) * self.size
        return (y,x)

    def get(self, idx):
        i,j = idx
        if 0 <= i < self.size and 0 <= j < self.size:
            return self.map[i,j]

        raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def set(self, idx, value=0):
        i,j = idx
        if 0 <= i < self.size and 0 <= j < self.size:
            self.map[i,j] = value
        else:
            raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def get_location(self, i, j):
        return get_location_meters(self.bl, i, j)

    def get_map(self):
        return self.map

    def handle_sensor(self, sensor_distance, angle):
        # Estimate the location of the point based on the distance from the 
        # distance sensor as well as our own angle.
        dy = math.sin(angle) * sensor_distance
        dx = math.cos(angle) * sensor_distance
        loc = get_location_meters(self.vehicle.location, dy, dx)

        print("Estimated location: {}, {}".format(loc.lat, loc.lon))

        # Place point location in the memory map.
        try:
            self.set(self.get_index(loc), 1)
        except KeyError:
            pass

# Main mission program
def main():
    # Connect to API provider and get vehicle object
    api = local_connect()
    vehicle = api.get_vehicles()[0]
    mission_settings = Settings("settings.json", "mission")

    mission = Mission(api, vehicle, mission_settings)

    # Make sure that mission being sent is displayed on console cleanly
    time.sleep(2)
    num_commands = mission.get_commands().count
    print("{} commands in the mission!".format(num_commands))

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff()

    print("Starting mission")
    # Set mode to AUTO to start mission
    vehicle.mode = VehicleMode("AUTO")
    vehicle.flush()

    # Monitor mission
    # We can get and set the command number and use convenience function for 
    # finding distance to an object or the next waypoint.

    sensors = [Distance_Sensor_Simulator(vehicle, angle) for angle in mission_settings.get("sensors")]
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
    memory_map = Memory_Map(vehicle, memory_size)

    # Temporary "cheat" to see 2d map of collision data
    for i in xrange(0,memory_size):
        for j in xrange(0,memory_size):
            loc = memory_map.get_location(i, j)
            if sensors[0].get_distance(loc) == 0:
                memory_map.set((i,j), 0.5)

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
            vehicle_idx = memory_map.get_index(vehicle.location)
            memory_map.set(vehicle_idx, -1)

            # Instead of performing an AUTO mission, we can also stand still 
            # and change the angle to look around. TODO: Make use of this when 
            # we're at a waypoint to look around? Make whole mission GUIDED?

            #mission.send_global_velocity(0,0,0)
            #vehicle.flush()
            #mission.set_yaw(yaw % 360, relative=False)
            #print("Velocity: {} m/s".format(vehicle.velocity))
            #print("Altitude: {} m".format(vehicle.location.alt))
            #print("Yaw: {} Expected: {}".format(vehicle.attitude.yaw*180/math.pi, yaw)

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
                    angle = sensor.get_angle(vehicle.attitude.yaw)
                    memory_map.handle_sensor(sensor_distance, angle)
                    sensor.draw_current_edge(plt, memory_map, colors[i])

                    print("=== [!] Distance to object: {} m (angle {}) ===".format(sensor_distance, angle))

                i = i + 1

            # Display the current memory map interactively.
            plt.imshow(memory_map.get_map(), origin='lower')
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
            memory_map.set(vehicle_idx, 0)
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
