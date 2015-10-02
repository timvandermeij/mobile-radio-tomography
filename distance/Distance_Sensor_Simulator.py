import sys
import math
from droneapi.lib import Location
from Distance_Sensor import Distance_Sensor
from ..settings import Settings

# Virtual sensor class that detects collision distances to simulated objects
class Distance_Sensor_Simulator(Distance_Sensor):
    def __init__(self, environment, angle=0):
        self.environment = environment
        self.geometry = self.environment.get_geometry()
        self.angle = angle
        self.settings = Settings("settings.json", "distance_sensor_simulator")
        # Margin in meters at which an object is still visible
        self.altitude_margin = self.settings.get("altitude_margin")
        # Maximum distance in meters that the sensor returns
        self.maximum_distance = self.settings.get("maximum_distance")

        # Tracking the relevant edge that the sensor detected
        self.current_edge = None

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

        edges = self.geometry.get_point_edges(points)
        inside = False
        for e in edges:
            if self.geometry.ray_intersects_segment(location, e[0], e[1]):
                inside = not inside

        return inside

    def get_edge_distance(self, edge, location, angle):
        """
        Calculate the distance in meters to the `edge` from a given `location` and `angle`.
        The `edge` is a tuple of Location points defining a (sloped) edge.
        """

        # Based on ray casting calculations from 
        # http://archive.gamedev.net/archive/reference/articles/article872.html 
        # except that the coordinate system there is assumed to revolve around 
        # the vehicle, which is strange. Instead, use a fixed origin and thus 
        # the edge's b1 is fixed, and calculate b2 instead.

        # TODO: Check whether calculations are correct and make use of more 
        # Geometry functions

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

            if m2 == m1:
                x = float('inf')
            else:
                x = (b1 - b2) / (m2 - m1)
            y = m1 * x + b1

        loc_point = Location(y, x, location.alt, location.is_relative)

        # Get altitude from edge
        edge_dist = self.geometry.get_distance_meters(edge[0], edge[1])
        point_dist = self.geometry.get_distance_meters(edge[1], loc_point)
        alt = edge[1].alt + ((edge[0].alt - edge[1].alt) / edge_dist) * point_dist

        if alt < location.alt - self.altitude_margin:
            return sys.float_info.max

        d = self.geometry.get_distance_meters(location, loc_point)

        return d

    def get_face_distance(self, face, location, angle):
        """
        Get the direction distance to a plane `face` given as a polygon in a list of points from the `location` with `angle`.
        Returns the distance as well as the edge that was closest to the location, if there is any.
        """
        # Check if angle is within at least one quadrant of the angles to the 
        # object bounds, and also within the object bounds themselves. Both 
        # requirements have to be met, otherwise angles that are around the 
        # 0 degree mark can confuse the latter check.
        angles = []
        quadrants = []
        q2 = int(angle / (0.5*math.pi))
        for point in face:
            ang = self.geometry.get_angle(location, point)

            # Try to put the angles "around" the object in case we are around 
            # 0 = 360 degrees.
            q1 = int(ang / (0.5*math.pi))
            if q1 == 0 and q2 == 3:
                ang = ang + 2*math.pi
            elif q1 == 3 and q2 == 0:
                ang = ang - 2*math.pi

            angles.append(ang)
            quadrants.append(q1)

        if q2 in quadrants and min(angles) < angle < max(angles):
            dists = []
            edges = self.geometry.get_point_edges(face)
            for edge in edges:
                dists.append(self.get_edge_distance(edge, location, angle))

            e_min = dists.index(min(dists))
            return (min(dists), edges[e_min])

        return (sys.float_info.max, None)

    def get_circle_distance(self, obj, location, angle):
        if obj['center'].alt >= location.alt - self.altitude_margin:
            # Find directional angle to the object's center.
            # The "object angle" should point "away" from the vehicle location, 
            # so that it matches up with the yaw if the vehicle is pointing 
            # toward the point.
            a2 = self.geometry.get_angle(location, obj['center'])
            diff = self.geometry.diff_angle(a2, angle)
            if abs(diff) < 5.0 * math.pi/180:
                d = self.geometry.get_distance_meters(location, obj['center'])
                return d - obj['radius']

        return sys.float_info.max

    def get_obj_distance(self, obj, location, angle):
        if isinstance(obj, list):
            # List of faces
            # TODO: Should not use just the edges of each face
            dists = []
            for face in obj:
                dist, edge = self.get_face_distance(face, location, angle)
                dists.append(dist)

            return (min(dists), None)
        if isinstance(obj, tuple):
            # Single face
            if self.point_inside_polygon(location, obj):
                return (0, None)

            return self.get_face_distance(obj, location, angle)
        elif 'center' in obj:
            return (self.get_circle_distance(obj, location, angle), obj['center'])

        return (self.maximum_distance, None)

    def get_distance(self, location=None, angle=None):
        """
        Get the distance in meters to the collision object from the current `location` (a Location object).
        """

        self.current_edge = None
        if location is None:
            location = self.environment.get_location()
        angle = self.get_angle(angle)

        distance = self.maximum_distance
        for obj in self.environment.objects:
            dist, edge = self.get_obj_distance(obj, location, angle)
            if dist < distance:
                distance = dist
                self.current_edge = edge

        return distance

    def get_angle(self, angle=None):
        """
        Convert a bearing angle to an angle that the distance sensor uses.
        """
        if angle is None:
            # Offset for the yaw being increasing clockwise and starting at 
            # 0 degrees when facing north rather than facing east.
            angle = self.geometry.bearing_to_angle(self.environment.get_yaw())

        # Add the the fixed angle of the sensor itself.
        # Ensure angle is always in the range [0, 2pi).
        return (angle + self.angle*math.pi/180) % (2*math.pi)
    
    def draw_current_edge(self, plt, map, color="red"):
        """
        Draw the edge that was detected during the previous distance sensor measurement, if any.
        The edge is drawn to the matplotlib plot object `plt` using the index offsets from the Memory_Map `map`. Additionally the `color` of the edge can be given.
        """
        if self.current_edge is not None:
            options = {
                "arrowstyle": "-",
                "color": color,
                "linewidth": 1
            }
            if isinstance(self.current_edge, tuple):
                e0 = map.get_index(self.current_edge[0])
                e1 = map.get_index(self.current_edge[1])
            else:
                e0 = map.get_index(self.current_edge)
                e1 = e0

            plt.annotate("", e0, e1, arrowprops=options)
