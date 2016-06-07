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

    def _is_x_inside(self, x):
        return x >= self._origin.x and x <= self._origin.x + self._width

    def _is_y_inside(self, y):
        return y >= self._origin.y and y <= self._origin.y + self._height

    def _is_intersecting(self, start, end):
        """
        Check if a line, defined by its `start` and `end` points, intersects
        with at least one of the four boundaries of the network.
        """

        if end.x - start.x == 0:
            # Vertical line, so only check intersection with the top and
            # bottom boundary.
            if not self._is_x_inside(end.x):
                return False

            y_min = min(end.y, start.y)
            y_max = max(end.y, start.y)
            y_top = self._origin.y + self._height
            return ((y_min <= self._origin.y and y_max >= self._origin.y) or
                    (y_min <= y_top and y_max >= y_top))

        if end.y - start.y == 0:
            # Horizontal line, so only check intersection with the left
            # and right boundary.
            if not self._is_y_inside(end.y):
                return False

            x_min = min(end.x, start.x)
            x_max = max(end.x, start.x)
            x_right = self._origin.x + self._width
            return ((x_min <= self._origin.x and x_max >= self._origin.x) or
                    (x_min <= x_right and x_max >= x_right))

        # Other line, so check intersection using the slope.
        return self._is_sloped_intersecting(start, end)

    def _is_sloped_intersecting(self, start, end):
        """
        Check if a line that is not exactly horizontal or vertical,
        defined by its `start` and `end` points, intersects with at least one
        of the four boundaries of the network.
        """

        # Non-straight line, so check intersection with all boundaries using 
        # the line equation y = ax + b.
        a = (end.y - start.y) / float(end.x - start.x)
        b = end.y - (a * end.x)

        # Check if the line intersects the left boundary.
        x_left = self._origin.x
        y_left = (a * x_left) + b
        if self._is_y_inside(y_left):
            return True

        # Check if the line intersects the right boundary.
        x_right = self._origin.x + self._width
        y_right = (a * x_right) + b
        if self._is_y_inside(y_right):
            return True

        # Check if the line intersects the top boundary.
        y_top = self._origin.y + self._height
        x_top = (y_top - b) / float(a)
        if self._is_x_inside(x_top):
            return True

        # Check if the line intersects the bottom boundary.
        y_bottom = self._origin.y
        x_bottom = (y_bottom - b) / float(a)
        return self._is_x_inside(x_bottom)

    def _get_boundary(self, point):
        """
        Check if a given point is positioned on a boundary.

        Returns the `Snap_Boundary` identifier for that boundary, or `False`
        if it is not on a boundary.
        """

        if self._is_x_inside(point.x):
            # On horizontal boundary or in between them.
            if point.y == self._origin.y:
                return Snap_Boundary.BOTTOM
            if point.y == self._origin.y + self._height:
                return Snap_Boundary.TOP

        if self._is_y_inside(point.y):
            # On vertical boundary or in between them.
            if point.x == self._origin.x:
                return Snap_Boundary.LEFT
            if point.x == self._origin.x + self._width:
                return Snap_Boundary.RIGHT

        return False

    def _snap_point(self, point, slope, previous_boundary=None):
        """
        Snap a single `point` of a link betweem two sensor points.

        The `point` is a tuple, and the `slope` is a floating point describing
        the slope of the line between the two points. `previous_boundary` is
        the boundary that the previous point was snapped to, or `None` if
        this is the first of the two points being snapped.

        Returns the snapped point and the boundary it was snapped to.
        """

        # There is no need to snap start or end points that are already on 
        # a boundary.
        boundary = self._get_boundary(point)
        if boundary != False:
            return point, boundary

        # Determine the location of the point relative to the boundaries; we 
        # want to snap to the closest boundary.
        if self._is_y_inside(point.y):
            if point.x <= self._origin.x:
                # Snap to left boundary.
                adjacent_side = abs(self._origin.x - point.x)
                opposite_side = slope * adjacent_side
                snapped_point = Point(point.x + adjacent_side,
                                      point.y + opposite_side)
                return snapped_point, Snap_Boundary.LEFT
            if point.x >= self._origin.x + self._width:
                # Snap to right boundary.
                adjacent_side = abs((self._origin.x + self._width) - point.x)
                opposite_side = slope * adjacent_side
                snapped_point = Point(point.x - adjacent_side,
                                      point.y - opposite_side)
                return snapped_point, Snap_Boundary.RIGHT

            # Otherwise, we are inside the network; snap away from the other 
            # point.
            return self._snap_point_inside(point, slope, previous_boundary)
        else:
            if point.y <= self._origin.y:
                # Snap to bottom boundary.
                opposite_side = abs(self._origin.y - point.y)
                adjacent_side = opposite_side / float(slope)
                snapped_point = Point(point.x + adjacent_side,
                                      point.y + opposite_side)
                return snapped_point, Snap_Boundary.BOTTOM

            # Snap to top boundary.
            opposite_side = abs((self._origin.y + self._height) - point.y)
            adjacent_side = opposite_side / float(slope)
            snapped_point = Point(point.x - adjacent_side,
                                  point.y - opposite_side)
            return snapped_point, Snap_Boundary.TOP

    def _snap_point_inside(self, point, slope, previous_boundary=None):
        """
        Snap a point tuple `point` that we determined to be inside the network
        to the closest boundary that is not `previous_boundary`.

        Returns the snapped point and the chosen boundary.
        """

        target_boundaries = [Snap_Boundary.LEFT]
        if slope < 0:
            target_boundaries.append(Snap_Boundary.TOP)
        else:
            target_boundaries.append(Snap_Boundary.BOTTOM)

        # Alter the x coordinate to the left or right boundary, depending on 
        # where the previous point was snapped to.
        if previous_boundary in target_boundaries:
            bx = self._origin.x + self._width
        else:
            bx = self._origin.x

        # Alter the y coordinate to the top or bottom boundary, depending on 
        # the slope of the line and where the previous point was snapped to.
        if (slope < 0) != (previous_boundary in target_boundaries):
            by = self._origin.y + self._height
        else:
            by = self._origin.y

        # Determine the options for snapping the line points to the boundary. 
        # Several options are possible when looking at the y and x components, 
        # because the difference in one component to the straight boundary may 
        # cause the other component to exit the network entirely.
        dx = point.x - bx
        dy = point.y - by
        xopts = (dx, dy / float(slope) if slope != 0 else dx)
        yopts = (dx * slope, dy)

        snapped_point = None
        boundary = None
        for opts in zip(xopts, yopts):
            candidate_point = Point(point.x - opts[0],
                                    point.y - opts[1])
            candidate_boundary = self._get_boundary(candidate_point)

            # If the candidate point is on a boundary, then it is a valid 
            # snapped point and we can immediately end the search.
            if candidate_boundary != False:
                snapped_point = candidate_point
                boundary = candidate_boundary
                break

        return snapped_point, boundary

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
        all_outside = all(outsiders)
        if not self._snap_inside and not all_outside:
            return None

        # Ensure that the line intersects at least one boundary of the network.
        if all_outside and not self._is_intersecting(start, end):
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
            snapped_point, previous_boundary = self._snap_point(point, slope,
                                                                previous_boundary)

            snapped_points.append(snapped_point)

        return list(order(snapped_points))
