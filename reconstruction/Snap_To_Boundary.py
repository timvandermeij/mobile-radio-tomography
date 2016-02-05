import math

class Snap_To_Boundary(object):
    def __init__(self, origin, width, height):
        """
        Initialize the snap to boundary object.
        """

        Point = namedtuple('Point', 'x y')
        self._origin = Point(origin[0], origin[1])
        self._width = width
        self._height = height

    def _is_outside(self, start, end):
        """
        Check if the start and end points of a line are outside the network.
        """

        start_in_network = (start.x > self._origin.x and
                            start.x < self._origin.x + self._width and
                            start.y > self._origin.y and
                            start.y < self._origin.y + self._height)
        end_in_network = (end.x > self._origin.x and
                          end.x < self._origin.x + self._width and
                          end.y > self._origin.y and
                          end.y < self._origin.y + self._height)
        return not (start_in_network or end_in_network)

    def _is_intersecting(self, start, end):
        """
        Check if a line, defined by its start and end points, is intersecting
        at least one of the four boundaries of the network.
        """

        # Compose the line equation y = ax + b.
        a = abs(end.y - start.y) / float(abs(end.x - start.x))
        b = end.y - (a * end.x)

        # Check if the line intersects the left boundary.
        x = self._origin.x
        y = (a * x) + b
        if y >= self._origin.y and y <= self._origin.y + self._height:
            return True

        # Check if the line intersects the right boundary.
        x = self._origin.x + self._width
        y = (a * x) + b
        if y >= self._origin.y and y <= self._origin.y + self._height:
            return True

        # Check if the line intersects the top boundary.
        y = self._origin.y + self._height
        x = (y - b) / float(a)
        if x >= self._origin.x and x <= self._origin.x + self._width:
            return True

        # Check if the line intersects the bottom boundary.
        y = self._origin.y
        x = (y - b) / float(a)
        if x >= self._origin.x and x <= self._origin.x + self._width:
            return True

        return False

    def execute(self, start, end):
        """
        Perform the snap to boundary algorithm.
        """

        Point = namedtuple('Point', 'x y')
        start = Point(start[0], start[1])
        end = Point(end[0], end[1])

        # Ensure that the start and end points are outside the network.
        if not self._is_outside(start, end):
            return []

        # Ensure that the line intersects at least one boundary of the network.
        if not self._is_intersecting(start, end):
            return []

        # Calculate the angle of the triangle.
        delta_x = abs(end.x - start.x)
        delta_y = abs(end.y - start.y)
        angle = math.atan2(delta_y, delta_x)

        # Snap the start and end points to the boundaries of the network.
        snapped_points = []
        for point in [start, end]:
            if point.y >= self._origin.y and point.y <= self._origin.y + self._height:
                if point.x <= self._origin.x:
                    # Snap to left boundary.
                    adjacent_side = abs(self._origin.x - point.x)
                    opposite_side = math.tan(angle) * adjacent_side
                    snapped_point = Point(point.x + adjacent_side, point.y + opposite_side)
                else:
                    # Snap to right boundary.
                    adjacent_side = abs((self._origin.x + self._width) - point.x)
                    opposite_side = math.tan(angle) * adjacent_side
                    snapped_point = Point(point.x - adjacent_side, point.y - opposite_side)
            else:
                if point.y <= self._origin.y:
                    # Snap to bottom boundary.
                    adjacent_side = abs(self._origin.y - point.y)
                    opposite_side = math.tan(angle) * adjacent_side
                    snapped_point = Point(point.y + adjacent_side, point.x - opposite_side)
                else:
                    # Snap to top boundary.
                    adjacent_side = abs((self._origin.y + self._height) - point.y)
                    opposite_side = math.tan(angle) * adjacent_side
                    snapped_point = Point(point.y - adjacent_side, point.x + opposite_side)

            snapped_points.append(snapped_point)

        return snapped_points
