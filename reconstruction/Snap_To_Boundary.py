from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])

class Snap_Boundary(object):
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4

class Snap_To_Boundary(object):
    def __init__(self, origin, width, height, snap_inside=False):
        """
        Initialize the snap to boundary object.
        """

        self._origin = Point(origin[0], origin[1])
        self._width = width
        self._height = height
        self._snap_inside = snap_inside

    def is_outside(self, point):
        """
        Check if a `Point` object `point` of is outside the network.
        """

        in_network = (point.x > self._origin.x and
                      point.x < self._origin.x + self._width and
                      point.y > self._origin.y and
                      point.y < self._origin.y + self._height)

        return not in_network

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

    def _get_boundary(self, point):
        """
        Check if a given point is positioned on a boundary.

        Returns the `Snap_Boundary` identifier for that boundary, or `False`
        if it is not on a boundary.
        """

        if point.x >= self._origin.x and point.x <= self._origin.x + self._width:
            # On horizontal boundary or in between them.
            if point.y == self._origin.y:
                return Snap_Boundary.BOTTOM
            if point.y == self._origin.y + self._height:
                return Snap_Boundary.TOP

        if point.y >= self._origin.y and point.y <= self._origin.y + self._height:
            # On vertical boundary or in between them.
            if point.x == self._origin.x:
                return Snap_Boundary.LEFT
            if point.x == self._origin.x + self._width:
                return Snap_Boundary.RIGHT

        return False

    def execute(self, start, end):
        """
        Perform the snap to boundary algorithm.
        """

        start = Point(start[0], start[1])
        end = Point(end[0], end[1])

        # Ensure that the start and end points are not the same point.
        if start == end:
            return None

        # Ensure that the start and end points are outside the network, unless 
        # the snapper is set to snap points inside the network as well.
        outsiders = [self.is_outside(point) for point in [start, end]]
        if not self._snap_inside and not all(outsiders):
            return None

        # Ensure that the line intersects at least one boundary of the network.
        if not self._is_intersecting(start, end):
            return None

        # Calculate the angle of the triangle.
        delta_x = end.x - start.x
        delta_y = end.y - start.y
        if delta_x == 0:
            slope = delta_y * float('inf')
        else:
            slope = delta_y / float(delta_x)

        # Snap the start and end points to the boundaries of the network.
        # Make sure we start with a point that has a known boundary beforehand, 
        # but ensure we order the output points as they were given in input.
        order = iter if outsiders[0] or not outsiders[1] else reversed
        snapped_points = []
        previous_boundary = None
        for point in order([start, end]):
            # There is no need to snap start or end points that are already on 
            # a boundary.
            boundary = self._get_boundary(point)
            if boundary != False:
                snapped_points.append(point)
                previous_boundary = boundary
                continue

            if point.y >= self._origin.y and point.y <= self._origin.y + self._height:
                if point.x <= self._origin.x:
                    # Snap to left boundary.
                    adjacent_side = abs(self._origin.x - point.x)
                    opposite_side = slope * adjacent_side
                    snapped_point = Point(point.x + adjacent_side,
                                          point.y + opposite_side)
                    previous_boundary = Snap_Boundary.LEFT
                elif point.x >= self._origin.x + self._width:
                    # Snap to right boundary.
                    adjacent_side = abs((self._origin.x + self._width) - point.x)
                    opposite_side = slope * adjacent_side
                    snapped_point = Point(point.x - adjacent_side,
                                          point.y - opposite_side)
                    previous_boundary = Snap_Boundary.RIGHT
                else:
                    # Inside the network; snap away from the other point.
                    target_boundaries = [Snap_Boundary.LEFT]
                    if slope < 0:
                        target_boundaries.append(Snap_Boundary.TOP)
                    else:
                        target_boundaries.append(Snap_Boundary.BOTTOM)

                    # Alter the x coordinate to the left or right boundary, 
                    # depending on where the previous point was snapped to.
                    if previous_boundary in target_boundaries:
                        bx = self._origin.x + self._width
                    else:
                        bx = self._origin.x

                    # Alter the y coordinate to the top or bottom boundary, 
                    # depending on the slope of the line and where the previous 
                    # point was snapped to.
                    if (slope < 0) != (previous_boundary in target_boundaries):
                        by = self._origin.y + self._height
                    else:
                        by = self._origin.y

                    dx = point.x - bx
                    dy = point.y - by
                    xopts = (dx, dy / float(slope) if slope != 0 else dx)
                    yopts = (dx * slope, dy)
                    snapped_point = None
                    for opts in zip(xopts, yopts):
                        snapped_point = Point(point.x - opts[0],
                                              point.y - opts[1])
                        boundary = self._get_boundary(snapped_point)
                        if boundary != False:
                            break

                    if snapped_point is None:
                        return None

                    previous_boundary = boundary
            else:
                if point.y <= self._origin.y:
                    # Snap to bottom boundary.
                    opposite_side = abs(self._origin.y - point.y)
                    adjacent_side = opposite_side / float(slope)
                    snapped_point = Point(point.x + adjacent_side,
                                          point.y + opposite_side)
                    previous_boundary = Snap_Boundary.BOTTOM
                else:
                    # Snap to top boundary.
                    opposite_side = abs((self._origin.y + self._height) - point.y)
                    adjacent_side = opposite_side / float(slope)
                    snapped_point = Point(point.x - adjacent_side,
                                          point.y - opposite_side)
                    previous_boundary = Snap_Boundary.TOP

            snapped_points.append(snapped_point)

        return list(order(snapped_points))
