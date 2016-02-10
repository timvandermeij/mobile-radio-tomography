from collections import namedtuple
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

        x = y = a = b = None
        if end.x - start.x == 0:
            # Vertical line, so only check intersection with the top and
            # bottom boundary.
            x = start.x
        elif end.y - start.y == 0:
            # Horizontal line, so only check intersection with the left
            # and right boundary.
            y = start.y
        else:
            # Other line, so check intersection with all boundaries using
            # the line equation y = ax + b.
            a = (end.y - start.y) / float(end.x - start.x)
            b = end.y - (a * end.x)

        if y is not None or (a is not None and b is not None):
            # Check if the line intersects the left boundary.
            x_left = self._origin.x
            y_left = (a * x_left) + b if y is None else y
            if y_left >= self._origin.y and y_left <= self._origin.y + self._height:
                return True

            # Check if the line intersects the right boundary.
            x_right = self._origin.x + self._width
            y_right = (a * x_right) + b if y is None else y
            if y_right >= self._origin.y and y_right <= self._origin.y + self._height:
                return True

        if x is not None or (a is not None and b is not None):
            # Check if the line intersects the top boundary.
            y_top = self._origin.y + self._height
            x_top = (y_top - b) / float(a) if x is None else x
            if x_top >= self._origin.x and x_top <= self._origin.x + self._width:
                return True

            # Check if the line intersects the bottom boundary.
            y_bottom = self._origin.y
            x_bottom = (y_bottom - b) / float(a) if x is None else x
            if x_bottom >= self._origin.x and x_bottom <= self._origin.x + self._width:
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
            return None

        # Ensure that the line intersects at least one boundary of the network.
        if not self._is_intersecting(start, end):
            return None

        # Calculate the angle of the triangle.
        delta_x = end.x - start.x
        delta_y = end.y - start.y
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
                    opposite_side = abs(self._origin.y - point.y)
                    adjacent_side = opposite_side / float(math.tan(angle))
                    snapped_point = Point(point.x + adjacent_side, point.y + opposite_side)
                else:
                    # Snap to top boundary.
                    opposite_side = abs((self._origin.y + self._height) - point.y)
                    adjacent_side = opposite_side / float(math.tan(angle))
                    snapped_point = Point(point.x - adjacent_side, point.y - opposite_side)

            snapped_points.append(snapped_point)

        return snapped_points
