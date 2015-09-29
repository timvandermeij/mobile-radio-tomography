import sys
import math
from droneapi.lib import Location
from Distance_Sensor import Distance_Sensor
from ..settings import Settings
from ..utils.Geometry import *

# Virtual sensor class that detects collision distances to simulated objects
class Distance_Sensor_Simulator(Distance_Sensor):
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.settings = Settings("settings.json", "distance_sensor_simulator")
        # Margin in meters at which an object is still visible
        self.altitude_margin = self.settings.get("altitude_margin")
        # Maximum distance in meters that the sensor returns
        self.maximum_distance = self.settings.get("maximum_distance")

        # TODO: Replace hardcoded objects with some sort of polygon database
        l1 = get_location_meters(self.vehicle.location, 100, 0, 10)
        l2 = get_location_meters(self.vehicle.location, 0, 100, 10)
        l3 = get_location_meters(self.vehicle.location, -100, 0, 10)
        l4 = get_location_meters(self.vehicle.location, 0, -100, 10)
        #l3 = get_location_meters(self.vehicle.location, 52.5, 22.5, 10)
        b = self.vehicle.location
        self.current_edge = None
        self.objects = [
            #{
            #    'center': get_location_meters(self.vehicle.location, 40, -10),
            #    'radius': 2.5,
            #},
            (get_location_meters(l1, 40, -40), get_location_meters(l1, 40, 40),
             get_location_meters(l1, -40, 40), get_location_meters(l1, -40, -40)),
            (get_location_meters(l2, 40, -40), get_location_meters(l2, 40, 40),
             get_location_meters(l2, -40, 40), get_location_meters(l2, -40, -40)),
            (get_location_meters(l3, 40, -40), get_location_meters(l3, 40, 40),
             get_location_meters(l3, -40, 40), get_location_meters(l3, -40, -40)),
            (get_location_meters(l4, 40, -40), get_location_meters(l4, 40, 40),
             get_location_meters(l4, -40, 40), get_location_meters(l4, -40, -40))
            #(get_location_meters(b, 50, -50), get_location_meters(b, 50, 50),
            # get_location_meters(b, -50, 50), get_location_meters(b, -50, 
            # -50))
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
            y = m2 * x + b2
        else:
            m1 = (edge[1].lat - edge[0].lat) / (edge[1].lon - edge[0].lon)
            if edge[1].lat < edge[0].lat:
                b1 = edge[1].lat - m1 * edge[1].lon
            else:
                b1 = edge[0].lat - m1 * edge[0].lon

            x = (b1 - b2) / (m2 - m1)
            y = m1 * x + b1

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

                e_min = dists.index(min(dists))
                self.current_edge = edges[e_min]
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

        return self.maximum_distance

    def get_distance(self, location=None, angle=None):
        """
        Get the distance in meters to the collision object from the current `location` (a Location object).
        """

        self.current_edge = None
        if location is None:
            location = self.vehicle.location
        if angle is None:
            # Offset for the yaw being increasing clockwise and starting at 
            # 0 degrees when facing north rather than facing east.
            angle = bearing_to_angle(self.vehicle.attitude.yaw)

        # Ensure angle is always in the range [0, 2pi).
        angle = angle % (2*math.pi)

        distance = self.maximum_distance
        for obj in self.objects:
            distance = min(distance, self.get_obj_distance(obj, location, angle))

        return distance
