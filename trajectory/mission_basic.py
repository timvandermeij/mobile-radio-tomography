"""
mission_basic.py: Example demonstrating basic mission operations including creating, clearing and monitoring missions.

Full documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import time
import math
from droneapi.lib import VehicleMode, Location, Command
from pymavlink import mavutil

# Connect to API provider and get vehicle
api = local_connect()
vehicle = api.get_vehicles()[0]


def get_location_metres(original_location, north, east):
    """
    Returns a Location object containing the latitude/longitude `north` and `east` (floating point) metres from the 
    specified `original_location`. The returned Location has the same `alt and `is_relative` values 
    as `original_location`.

    The function is useful when you want to move the vehicle around specifying locations relative to 
    the current vehicle position.
    The algorithm is relatively accurate over small distances (10m within 1km) except close to the poles.
    For more information see:
    http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
    """
    earth_radius=6378137.0 #Radius of "spherical" earth
    #Coordinate offsets in radians
    lat = north / earth_radius
    lon = east / (earth_radius*math.cos(math.pi*original_location.lat/180))

    #New position in decimal degrees
    newlat = original_location.lat + (lat * 180/math.pi)
    newlon = original_location.lon + (lon * 180/math.pi)
    return Location(newlat, newlon,original_location.alt,original_location.is_relative)


def get_distance_metres(location1, location2):
    """
    Returns the ground distance in metres between two Location objects.

    This method is an approximation, and will not be accurate over large distances and close to the 
    earth's poles. It comes from the ArduPilot test code: 
    https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
    """
    dlat = location2.lat - location1.lat
    dlong = location2.lon - location1.lon
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5



def distance_to_current_waypoint():
    """
    Gets distance in metres to the current waypoint. 
    It returns None for the first waypoint (Home location).
    """
    nextwaypoint = vehicle.commands.next
    if nextwaypoint == 1:
        return None
    missionitem = vehicle.commands[nextwaypoint]
    lat = missionitem.x
    lon = missionitem.y
    alt = missionitem.z
    targetWaypointLocation = Location(lat, lon, alt, is_relative=True)
    distancetopoint = get_distance_metres(vehicle.location,  targetWaypointLocation)
    return distancetopoint


def clear_mission():
    """
    Clear the current mission.
    """
    cmds = vehicle.commands
    vehicle.commands.clear()
    vehicle.flush()

    # After clearing the mission you MUST re-download the mission from the vehicle 
    # before vehicle.commands can be used again
    # (see https://github.com/dronekit/dronekit-python/issues/230)
    cmds = vehicle.commands
    cmds.download()
    cmds.wait_valid()
    

def download_mission():
    """
    Download the current mission from the vehicle.
    """
    cmds = vehicle.commands
    cmds.download()
    cmds.wait_valid() # wait until download is complete.


def add_square_mission(location, size):
    """
    Adds a takeoff command and four waypoint commands to the current mission. 
    The waypoints are positioned to form a square of side length `2*size` around the specified `location`.

    The function assumes vehicle.commands matches the vehicle mission state 
    (you must have called download at least once in the session and after clearing the mission)
    """
    # Add the commands. The meaning/order of the parameters is documented in the Command class.
    cmds = vehicle.commands
    #Add MAV_CMD_NAV_TAKEOFF command. This is ignored if the vehicle is already in the air.
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 0, 10))

    #Define the four MAV_CMD_NAV_WAYPOINT locations and add the commands
    point1 = get_location_metres(location, size, -size)
    point2 = get_location_metres(location, size, size)
    point3 = get_location_metres(location, -size, size)
    point4 = get_location_metres(location, -size, -size)
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point1.lat, point1.lon, 11))
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point2.lat, point2.lon, 12))
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point3.lat, point3.lon, 13))
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point4.lat, point4.lon, 14))
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point1.lat, point1.lon, 15))

    # Send commands to vehicle.
    vehicle.flush()

    return cmds.count


def arm_and_takeoff(targetAltitude):
    """
    Arms vehicle and fly to targetAltitude.
    """
    print "Basic pre-arm checks"
    # Don't let the user try to fly autopilot is booting
    while vehicle.mode.name == "INITIALISING":
        print "Waiting for vehicle to initialise..."
        time.sleep(1)
    while vehicle.gps_0.fix_type < 2:
        print "Waiting for GPS...:", vehicle.gps_0.fix_type
        time.sleep(1)

    print "Arming motors"
    # Copter should arm in GUIDED mode
    vehicle.mode    = VehicleMode("GUIDED")
    vehicle.armed   = True
    vehicle.flush()

    while not vehicle.armed and not api.exit:
        print " Waiting for arming..."
        time.sleep(1)

    print "Taking off!"
    vehicle.commands.takeoff(targetAltitude) # Take off to target altitude
    vehicle.flush()

    # Wait until the vehicle reaches a safe height before processing the goto 
    # (otherwise the command after Vehicle.commands.takeoff will execute 
    # immediately).
    while not api.exit:
        print " Altitude: ", vehicle.location.alt
        #Just below target, in case of undershoot.
        if vehicle.location.alt >= targetAltitude * 0.95:
            print "Reached target altitude"
            break
        time.sleep(1)


print "Clear the current mission"
clear_mission()

print "Create a new mission"
size = 50
num_commands = add_square_mission(vehicle.location, size)
print "%d commands in the mission!" % num_commands
time.sleep(2)  # This is here so that mission being sent is displayed on console


# From Copter 3.3 you will be able to take off using a mission item. Plane must take off using a mission item (currently).
arm_and_takeoff(10)

print "Starting mission"
# Set mode to AUTO to start mission
vehicle.mode = VehicleMode("AUTO")
vehicle.flush()

# Monitor mission. 
# Demonstrates getting and setting the command number 
# Uses distance_to_current_waypoint(), a convenience function for finding the 
#   distance to the next waypoint.

while True:
    nextwaypoint = vehicle.commands.next
    distance = distance_to_current_waypoint()
    if nextwaypoint > 1:
        print "Distance to waypoint (%s): %s" % (nextwaypoint, distance)
        if distance < size / 2:
            print "Somewhat rounded: skip to next waypoint"
            vehicle.commands.next = nextwaypoint + 1
            nextwaypoint = nextwaypoint + 1
    if nextwaypoint >= num_commands:
        print "Exit 'standard' mission when heading for final waypoint (%d)" % num_commands
        break

    time.sleep(1)

print "Return to launch"
vehicle.mode = VehicleMode("RTL")
vehicle.flush()  # Flush to ensure changes are sent to autopilot


