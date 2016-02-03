import math

class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "({}, {})".format(self.x, self.y)

class Snap_To_Boundary(object):
    def __init__(self, origin, width, height):
        """
        Initialize the snap to boundary object.
        """

        self._origin = Point(origin[0], origin[1])
        self._width = width
        self._height = height

    def execute(self, start, end):
        """
        Perform the snap to boundary algorithm.
        """

        start = Point(start[0], start[1])
        end = Point(end[0], end[1])

        # Ensure that the start and end points are not inside the network.
        start_in_network = (start.x > self._origin.x and
                            start.x < self._origin.x + self._width and
                            start.y > self._origin.y and
                            start.y < self._origin.y + self._height)
        end_in_network = (end.x > self._origin.x and
                          end.x < self._origin.x + self._width and
                          end.y > self._origin.y and
                          end.y < self._origin.y + self._height)
        if start_in_network or end_in_network:
            return None

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
