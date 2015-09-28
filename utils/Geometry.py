import sys
import math
from droneapi.lib import Location

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