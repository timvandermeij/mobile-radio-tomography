"""
mission_basic.py: Example demonstrating basic mission operations including creating, clearing and monitoring missions.

Full documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import time
import math
from droneapi.lib import VehicleMode, Location, Command
from pymavlink import mavutil

# Geometry utility functions
# These calculate distances, locations or angles based on specific input.
# Note that some functions assume certain properties of the earth's surface, 
# such as it being spherical or being flat. Depending on these assumptions, 
# these functions may have different accuracies across distances.
# Note that (y,x) = (lat,lon) = (N,E).

def get_location_meters(original_location, north, east, alt=0):
    """
    Returns a Location object containing the latitude/longitude `north` and `east` (floating point) meters from the 
    specified `original_location`, and optionally `alt` meters above the `original_location`. The returned Location has the same and `is_relative` value as `original_location`.

    The function is useful when you want to move the vehicle around specifying locations relative to 
    the current vehicle position.
    The algorithm is relatively accurate over small distances (10m within 1km) except close to the poles.
    For more information see:
    http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
    """
    # Radius of "spherical" earth
    earth_radius = 6378137.0
    # Coordinate offsets in radians
    lat = north / earth_radius
    lon = east / (earth_radius * math.cos(original_location.lat * math.pi/180))

    # New position in decimal degrees
    newlat = original_location.lat + (lat * 180/math.pi)
    newlon = original_location.lon + (lon * 180/math.pi)
    return Location(newlat, newlon, original_location.alt + alt, original_location.is_relative)


def get_distance_meters(location1, location2):
    """
    Returns the ground distance in meters between two Location objects.

    This method is an approximation, and will not be accurate over large distances and close to the 
    earth's poles. It comes from the ArduPilot test code: 
    https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
    """
    dlat = location2.lat - location1.lat
    dlong = location2.lon - location1.lon
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5


def ray_intersects_segment(P, start, end):
    '''
    Given a location point `P` and an edge of two endpoints `start` and `end` of a line segment, returns boolean whether the ray starting from the point eastward intersects the edge.
    '''
    # Based on http://rosettacode.org/wiki/Ray-casting_algorithm#Python but
    # removed some edge cases and clarified somewhat
    if start.lat > end.lat:
        # Swap start and end of segment
        start,end = end,start

    if P.lat < start.lat or P.lat > end.lat or P.lon > max(start.lon, end.lon):
        return False
    if P.lon < min(start.lon, end.lon):
        return True

    if abs(start.lon - end.lon) < sys.float_info.min:
        ang_out = (end.lat - start.lat) / (end.lon - start.lon)
    else:
        ang_out = sys.float_info.max

    if abs(start.lon - P.lon) < sys.float_info.min:
        ang_in = (P.lat - start.lat) / (P.lon - start.lon)
    else:
        ang_in = sys.float_info.max

    return ang_in >= ang_out

def get_point_edges(points):
    """
    From a given list of `points` in a polygon (sorted on edge positions), generate a list of edges, which are tuples of two points of the line segment.
    """
    return zip(points, list(points[1:]) + [points[0]])

def get_angle(locA, locB):
    """
    Get the angle in radians for the segment between locations `locA` and `locB` compared to the cardinal directions.

    Does not yet take curvature of earth in account, and should thus be used only for close locations.
    """

    if locA.lon == locB.lon:
        angle = math.pi/2.0
    else:
        angle = math.atan(abs(locA.lat - locB.lat) / abs(locA.lon - locB.lon))

    # Flip the angle into the correct quadrant based on non-absolute difference
    # We use radians so pi rad = 180 degrees and 2*pi rad = 360 degrees
    if locB.lon < locA.lon:
        angle = math.pi - angle
    if locB.lat < locA.lat:
        angle = 2*math.pi - angle

    return angle % (2*math.pi)

def diff_angle(a1, a2):
    # Based on http://stackoverflow.com/a/7869457 but for radial angles
    return (a1 - a2 + math.pi) % (2*math.pi) - math.pi

# Virtual sensor class that detects collision distances to simulated objects
class Sensor(object):
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.altitude_margin = 2.5
        l2 = get_location_meters(self.vehicle.location, 50, -50, 10)
        l3 = get_location_meters(self.vehicle.location, 52.5, 22.5, 10)
        self.objects = [
            {
                'center': get_location_meters(self.vehicle.location, 40, -10),
                'radius': 2.5,
            },
            (get_location_meters(l2, 5, -5), get_location_meters(l2, 5, 5),
             get_location_meters(l2, -5, 5), get_location_meters(l2, -5, -5)),
            (get_location_meters(l3, 5, 0), get_location_meters(l3, 0, 5),
             get_location_meters(l3, -5, 0), get_location_meters(l3, 0, -5))
        ]

    def point_inside_polygon(self, location, points):
        """
        Detect objectively whether the vehicle has flown into an object.
        """
        # Simplification: if the point is above the mean altitude of all the 
        # points, then do not consider it to be inside the polygon. We could 
        # also perform interesting calculations here, but we won't have that 
        # many objects of differing altitude anyway.
        avg_alt = float(sum([point.alt for point in points]))/len(points)
        if avg_alt < location.alt - self.altitude_margin:
            return False

        edges = get_point_edges(points)
        num = sum(ray_intersects_segment(location, e[0], e[1]) for e in edges)
        return num % 2 == 1

    def get_edge_distance(self, edge, location, angle):
        # Based on ray casting calculations from 
        # http://archive.gamedev.net/archive/reference/articles/article872.html 
        # except that the coordinate system there is assumed tp revolve around 
        # the vehicle, which is strange. Instead, use a fixed origin and thus 
        # the edge's b1 is fixed, and calculate b2 instead.

        m2 = math.tan(angle)
        b2 = location.lat - m2 * location.lon

        if edge[1].lon == edge[0].lon:
            # Prevent division by zero
            # This should usually become inf, but since m2 is calculated with 
            # math.tan as well we should use the maximal value that this 
            # function reaches.
            m1 = math.tan(math.pi/2)
            b1 = 0.0
            x = edge[0].lon
        else:
            m1 = (edge[1].lat - edge[0].lat) / (edge[1].lon - edge[0].lon)
            if edge[1].lat < edge[0].lat:
                b1 = edge[1].lat - m1 * edge[1].lon
            else:
                b1 = edge[0].lat - m1 * edge[0].lon

            x = (b1 - b2) / (m2 - m1)

        y = m2 * x + b2

        loc_point = Location(y, x, location.alt, location.is_relative)

        # Get altitude from edge
        edge_dist = get_distance_meters(edge[0], edge[1])
        point_dist = get_distance_meters(edge[1], loc_point)
        alt = edge[1].alt + ((edge[0].alt - edge[1].alt) / edge_dist) * point_dist

        if alt < location.alt - self.altitude_margin:
            print('Not visible due to altitude alt={} v={}'.format(alt, location.alt))
            return sys.float_info.max

        d = get_distance_meters(location, loc_point)

        return d

    def get_obj_distance(self, obj, location, angle):
        if isinstance(obj, tuple):
            if self.point_inside_polygon(location, obj):
                return 0

            # Check if angle is within at least one quadrant of the angles to 
            # the object bounds, and also within the object bounds themselves. 
            # Both requirements have to be met, otherwise angles that are 
            # around the 0 degree mark can confuse the latter check.
            angles = []
            quadrants = []
            q2 = int(angle / (0.5*math.pi))
            for point in obj:
                ang = get_angle(location, point)

                # Try to put the angles "around" the object in case we are 
                # around 0 = 360 degrees.
                q1 = int(ang / (0.5*math.pi))
                if q1 == 0 and q2 == 3:
                    ang = ang + 2*math.pi
                elif q1 == 3 and q2 == 0:
                    ang = ang - 2*math.pi

                angles.append(ang)
                quadrants.append(q1)

            if q2 in quadrants and min(angles) < angle < max(angles):
                dists = []
                edges = get_point_edges(obj)
                for edge in edges:
                    dists.append(self.get_edge_distance(edge, location, angle))

                return min(dists)
        elif 'center' in obj:
            if obj['center'].alt >= location.alt - self.altitude_margin:
                # Find directional angle to the object's center.
                # The "object angle" should point "away" from the vehicle 
                # location, so that it matches up with the yaw if the vehicle 
                # is pointing toward the point.
                a2 = get_angle(location, obj['center'])
                diff = diff_angle(a2, angle)
                if abs(diff) < 5.0 * math.pi/180:
                    return get_distance_meters(location, obj['center']) - obj['radius']
            else:
                print('Not visible due to altitude, vehicle={}'.format(location.alt))

        return sys.float_info.max

    def get_distance(self, location=None, angle=None):
        """
        Get the distance in meters to the collision object from the current `location` (a Location object).
        """

        if location is None:
            location = self.vehicle.location
        if angle is None:
            # Offset for the yaw being increasing counterclockwise and starting 
            # at 0 degrees when facing north rather than facing east.
            angle = -(self.vehicle.attitude.yaw - math.pi/2.0)

        # Ensure angle is always in the range [0, 2pi).
        angle = angle % (2*math.pi)

        distance = sys.float_info.max
        for obj in self.objects:
            distance = min(distance, self.get_obj_distance(obj, location, angle))

        # TODO: Replace with a parameter that has a limit on the measured 
        # sensor distance, similar to what the ArduPilot simulator does?
        return distance

# Mission utility functions

class Mission(object):
    def __init__(self, api, vehicle):
        self.api = api
        self.vehicle = vehicle

    def distance_to_current_waypoint(self):
        """
        Gets distance in meters to the current waypoint. 
        It returns `None` for the first waypoint (Home location).
        """
        next_waypoint = self.vehicle.commands.next
        if next_waypoint == 1:
            return None
        mission_item = self.vehicle.commands[next_waypoint]
        lat = mission_item.x
        lon = mission_item.y
        alt = mission_item.z
        waypoint_location = Location(lat, lon, alt, is_relative=True)
        distance = get_distance_meters(self.vehicle.location, waypoint_location)
        return distance

    def clear_mission(self):
        """
        Clear the current mission.
        """
        cmds = self.vehicle.commands
        self.vehicle.commands.clear()
        self.vehicle.flush()

        # After clearing the mission, we MUST re-download the mission from the 
        # vehicle before vehicle.commands can be used again.
        # See https://github.com/dronekit/dronekit-python/issues/230 for 
        # reasoning.
        self.download_mission()

    def download_mission(self):
        """
        Download the current mission from the vehicle.
        """
        cmds = self.vehicle.commands
        cmds.download()
        # Wait until download is complete.
        cmds.wait_valid()

    def add_square_mission(self, center, size):
        """
        Adds a takeoff command and four waypoint commands to the current mission. 
        The waypoints are positioned to form a square of side length `2*size` around the specified `center` Location.

        The function assumes `vehicle.commands` is the vehicle mission state 
        (you must have called `download_mission` at least once before in the session and after any use of `clear_mission`)
        """
        # Add the commands. The meaning/order of the parameters is documented 
        # in the Command class.
        cmds = self.vehicle.commands
        # Add MAV_CMD_NAV_TAKEOFF command. This is ignored if the vehicle is 
        # already in the air.
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 0, 10))

        # Define the four MAV_CMD_NAV_WAYPOINT locations and add the commands
        point1 = get_location_meters(center, size, -size)
        point2 = get_location_meters(center, size, size)
        point3 = get_location_meters(center, -size, size)
        point4 = get_location_meters(center, -size, -size)
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point1.lat, point1.lon, 11))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point2.lat, point2.lon, 12))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point3.lat, point3.lon, 13))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point4.lat, point4.lon, 14))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point1.lat, point1.lon, 15))

        # Send commands to vehicle.
        self.vehicle.flush()

        return cmds.count


    def arm_and_takeoff(self, targetAltitude):
        """
        Arms vehicle and fly to targetAltitude.
        """
        print "Basic pre-arm checks"
        # Don't let the user try to fly autopilot is booting
        while self.vehicle.mode.name == "INITIALISING":
            print "Waiting for vehicle to initialise..."
            time.sleep(1)
        while self.vehicle.gps_0.fix_type < 2:
            print "Waiting for GPS...:", self.vehicle.gps_0.fix_type
            time.sleep(1)

        print "Arming motors"
        # Copter should arm in GUIDED mode
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.armed = True
        self.vehicle.flush()

        while not self.vehicle.armed and not self.api.exit:
            print " Waiting for arming..."
            time.sleep(1)

        # Take off to target altitude
        print "Taking off!"
        self.vehicle.commands.takeoff(targetAltitude)
        self.vehicle.flush()

        # Wait until the vehicle reaches a safe height before processing the 
        # goto (otherwise the command after Vehicle.commands.takeoff will 
        # execute immediately).
        while not self.api.exit:
            # TODO: Check sensors here already?
            print " Altitude: ", self.vehicle.location.alt
            # Just below target, in case of undershoot.
            if self.vehicle.location.alt >= targetAltitude * 0.95:
                print "Reached target altitude"
                break
            time.sleep(1)

    def set_speed(self, speed):
        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # command
            0, # confirmation
            0, # param 1
            speed, # speed in meters/second
            0, 0, 0, 0, 0 # param 3 - 7
        )

        # Send command to vehicle
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()

# Main mission program
def main():
    # Connect to API provider and get vehicle object
    api = local_connect()
    vehicle = api.get_vehicles()[0]

    mission = Mission(api, vehicle)
    print "Clear the current mission"
    mission.clear_mission()

    print "Create a new mission"
    size = 50
    num_commands = mission.add_square_mission(vehicle.location, size)
    print "%d commands in the mission!" % num_commands
    # Make sure that mission being sent is displayed on console cleanly
    time.sleep(2)

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff(10)

    print "Starting mission"
    # Set mode to AUTO to start mission
    vehicle.mode = VehicleMode("AUTO")
    vehicle.flush()

    # Monitor mission
    # We can get and set the command number and use convenience function for 
    # finding distance to an object or the next waypoint.

    sensor = Sensor(vehicle)
    closeness = 2.0
    farness = 100.0
    while True:
        sensor_distance = sensor.get_distance(vehicle.location)
        if sensor_distance < farness:
            print "Distance to object: %s m" % sensor_distance
            if sensor_distance < closeness:
                print "Too close to the object, halting."
                vehicle.mode = VehicleMode("GUIDED")
                mission.set_speed(0)
                if sensor_distance == 0:
                    print "Inside the object, abort mission."
                    sys.exit(1)
                else:
                    break

        nextwaypoint = vehicle.commands.next
        distance = mission.distance_to_current_waypoint()
        if nextwaypoint > 1:
            if distance < farness:
                print "Distance to waypoint (%s): %s m" % (nextwaypoint, distance)
                if distance < closeness:
                    print "Close enough: skip to next waypoint"
                    vehicle.commands.next = nextwaypoint + 1
                    nextwaypoint = nextwaypoint + 1

        if nextwaypoint >= num_commands:
            print "Exit 'standard' mission when heading for final waypoint (%d)" % num_commands
            break

        time.sleep(0.5)

    print "Return to launch"
    vehicle.mode = VehicleMode("RTL")
    # Flush to ensure changes are sent to autopilot
    vehicle.flush()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file.
if __name__ in ["__main__", "__builtin__"]:
    main()
