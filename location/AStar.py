from collections import deque
import math
import numpy as np

class AStar(object):
    """
    An A* search algorithm that works on a grid-like memory map containing free
    paths and detected objects.
    """

    def __init__(self, geometry, memory_map, allow_at_bounds=False,
                 use_indices=False):
        """
        Initialize the A* search algorithm. The given `geometry` is a `Geometry`
        object for the space, and `memory_map` is a `Memory_Map` for the part of
        the space that the vehicle operates in.

        If `allow_at_bounds` is `True`, then the boundary of the memory map is
        acceptable for the vehicle to be situated in, otherwise these locations
        are skipped when creating a path to the location. Setting this to `True`
        is useful for robot vehicles that operate on a fixed-size grid.

        If `use_indices` is `True`, then memory map indices are reconstructed
        instead of Location objects.
        """

        self._geometry = geometry
        self._norm = self._geometry.norm
        self._memory_map = memory_map

        self._allow_at_bounds = allow_at_bounds
        self._use_indices = use_indices

        self._neighbors = self._geometry.get_neighbor_offsets()
        self._neighbor_directions = self._geometry.get_neighbor_directions()
        self._resolution = float(self._memory_map.get_resolution())
        self._size = self._memory_map.get_size()

        # Cache of location objects retrieved from the memory map, by their 
        # memory map index.
        self._locations = {}

        # A set of indices that are out of bounds but reachable in one step 
        # during the assignment.
        self._out_of_bounds = set()
        self._out_of_bounds.update([(-1, i) for i in range(-1, self._size + 1)])
        self._out_of_bounds.update([(i, -1) for i in range(-1, self._size + 1)])
        self._out_of_bounds.update([
            (self._size, i) for i in range(-1, self._size + 1)
        ])
        self._out_of_bounds.update([
            (i, self._size) for i in range(-1, self._size + 1)
        ])

        # State variables used during the search algorithm.
        self._close = None
        self._evaluated = None
        self._open_nodes = None
        self._came_from = None

        self._d = None
        self._f = None
        self._g = None

    def _get_close_map(self, closeness):
        """
        Calculate a numpy array containing the areas of influence as binary
        pixel values.

        The areas of influence have a radius of at most `closeness` meters.
        If `closeness` is `1` and the memory map resolution is as well, then
        this is equal to the detected objects in the memory map.
        """

        if closeness == 1 and self._resolution == 1:
            # If the closeness and resolution are both `1`, then this means 
            # each object's region of influence is the (detected) object 
            # itself. Thus we can make direct use of the memory map instead of 
            # rebuilding it.
            return self._memory_map.get_map()

        # Calculate the regions of influence of the objects in the memory map.
        # We consider these regions to be too close and thus unsafe.
        nonzero = self._memory_map.get_nonzero_array()
        # The closeness radius in memory map coordinate units
        radius = (closeness * self._resolution)**2
        close = np.zeros((self._size, self._size))
        for idx in nonzero:
            # Center of the mask
            a, b = idx
            # Open meshlike grid
            y, x = np.ogrid[-a:self._size-a, -b:self._size-b]
            # The circular mask of the region of influence of the object. This 
            # region is too close to that object.
            mask = x*x + y*y < radius
            close[mask] = 1

        return close

    def _get_location(self, idx):
        """
        Retrieve the location for the memory map index `idx`.

        Uses a cache if the location was used before, or the memory map
        otherwise.
        """

        if idx not in self._locations:
            self._locations[idx] = self._memory_map.get_location(*idx)

        return self._locations[idx]

    def assign(self, start, goal, closeness, direction=None, turning_cost=0.0):
        """
        Perform the A* search algorithm to create a list of waypoints that bring
        the vehicle from the position `start` to the position `goal` while not
        going through objects or getting closer than `closeness` meters (or grid
        units) to them. `direction` specifies the initial direction and
        `turning_cost` is the additional cost added to distances between points
        if the vehicle needs to turn to travel between them.

        If `use_indices` is enabled, then `start` and `goal` are memory map
        indexes, otherwise they are `Location` objects.

        The `direction` is the initial yaw angle that the vehicle has at this
        point; this can be used to find a more optimal path by reducing the
        turns needed, at least if `turning_cost` is set to a nonzero value that
        provides a scale between the a turn's radians and the distance that
        a vehicle could travel in the same time as such a turn.

        When a safe and fast path is found, then it returns a tuple. The first
        value is the list of `Location` objects or memory map indexes, depending
        on `use_indices`, that describe path waypoints. The second value is the
        same list except with only those waypoints that matter in the traversal
        of the vehicle, i.e., removing points that follow the same trend.
        The third value is the distance cost, and the fourth value is the
        direction yaw angle of the vehicle at the goal point.

        If no such assignment can be found, then an empty list, infinity and
        the original `direction` are returned.
        """

        if self._use_indices:
            start_idx = tuple(start)
            goal_idx = tuple(goal)
        else:
            start_idx = self._memory_map.get_index(start)
            goal_idx = self._memory_map.get_index(goal)

        self._close = self._get_close_map(closeness)

        if start_idx == goal_idx:
            # Already at the requested location, simply return it as the 
            # waypoint even if this location is unsafe (since stoppping is 
            # considered a safe action). Note that `goal == goal_idx` when 
            # `use_indices` is enabled.
            return [goal], [goal], 0.0, direction

        if not self._memory_map.index_in_bounds(*goal_idx):
            # No safe path to the location since the location is outside of the 
            # memory map.
            return [], [], np.inf, direction

        if self._close[goal_idx]:
            # No safe path to the location since the location is unsafe, due to 
            # being too close to an object.
            return [], [], np.inf, direction

        # If we are allowed to move on the bounds of the memory map, but not 
        # outside it, then we can speed up the out of bounds check by 
        # considering these indices as evaluated. Thus they are skipped without 
        # having a memory map call overhead.
        self._evaluated = set()
        if self._allow_at_bounds:
            self._evaluated.update(self._out_of_bounds)

        self._open_nodes = set([start_idx])
        self._came_from = {}

        # Direction of the vehicle along best known path
        self._d = np.full((self._size, self._size), np.nan)
        self._d[start_idx] = direction

        # Estimated total cost from start to goal when passing through 
        # a specific index whose best known path is already known.
        self._f = np.full((self._size, self._size), np.inf)
        self._f[start_idx] = self._get_cost(start_idx, goal_idx, turning_cost)

        # Cost along best known path
        self._g = np.full((self._size, self._size), np.inf)
        self._g[start_idx] = 0.0

        return self._search(start_idx, goal_idx, closeness, turning_cost)

    def _search(self, start_idx, goal_idx, closeness, turning_cost):
        """
        Perform the actual search algorithm after initial setup.

        The `start_idx` and `goal_idx` are memory map indexes of the start and
        goal locations, respectively. The other arguments as well as the return
        value are the same as the `assign` method.
        """

        while self._open_nodes:
            # Get the node in open_nodes with the lowest f score
            open_indices = zip(*self._open_nodes)
            min_idx = np.argmin(self._f[open_indices])
            current_idx = (open_indices[0][min_idx], open_indices[1][min_idx])

            # If we reached the goal index, then we have found the fastest 
            # safest path to it, thus reconstruct this path.
            if current_idx == goal_idx:
                path, trending_path = self._reconstruct(goal_idx)
                return path, trending_path, self._g[goal_idx], self._d[goal_idx]

            # Evaluate the new node
            self._open_nodes.remove(current_idx)
            self._evaluated.add(current_idx)

            neighborhood = zip(current_idx + self._neighbors,
                               self._neighbor_directions)
            for neighbor_coord, neighbor_direction in neighborhood:
                # Create the neighbor index and check whether we have evaluated 
                # it before.
                neighbor_idx = tuple(neighbor_coord)
                if neighbor_idx in self._evaluated:
                    continue

                # Check whether the neighbor index is still in bounds. We can 
                # break if it is not in bounds, because that means that the 
                # current location is close to the memory map bounds, which 
                # could be considered unsafe. But if we have the possibility to 
                # move at the boundary, then try the next neighbor instead.
                # When `allow_at_bounds` is enabled, then this check is already 
                # performed when checking for evaluated neighbors.
                if not self._allow_at_bounds and \
                   not self._memory_map.index_in_bounds(*neighbor_idx):
                    break

                # Check whether the neighbor index is inside the region of 
                # influence of any other object. Only do so when we are not 
                # leaving a region of influence around the start location, 
                # since we should be able to leave this region if it exists.
                if self._close[neighbor_idx]:
                    if self._left_start_area(start_idx, current_idx, closeness):
                        continue

                # Calculate the new tentative distances to the point
                cost = self._get_cost(current_idx, neighbor_idx, turning_cost,
                                      direction=neighbor_direction)
                tentative_g = self._g[current_idx] + cost
                if tentative_g >= self._g[neighbor_idx]:
                    # Not a better path, thus we do not need to update anything 
                    # for this neighbor which has a different, faster path.
                    continue

                self._open_nodes.add(neighbor_idx)
                self._came_from[neighbor_idx] = current_idx
                self._g[neighbor_idx] = tentative_g

                predicted_cost = self._get_cost(neighbor_idx, goal_idx,
                                                turning_cost)
                self._f[neighbor_idx] = tentative_g + predicted_cost
                self._d[neighbor_idx] = neighbor_direction

        direction = None if np.isnan(self._d[start_idx]) else self._d[start_idx]
        return [], [], np.inf, direction

    def _left_start_area(self, start_idx, current_idx, closeness):
        """
        Check whether the memory map index `current_idx` is outside of the
        area of influence that the starting location of `start_idx` is also in.

        The area of influence is at most `closeness` meters in radius. If there
        is no such area of influence, then we have always left the area.
        """

        return not self._close[start_idx] or self._g[current_idx] >= closeness

    def _reconstruct(self, current):
        """
        Reconstruct the path from the starting location to `current`, a memory
        map index of the goal location. This only works once the optimal path
        to the goal has been found in `_search`.

        The resulting lists contain either memory map index tuples or `Location`
        objects, depending on the `use_indices` constructor argument. The first
        list contains all intermediate memory map points, while the second
        contains only those that matter in the vehicle's trajectory.
        """

        # The path from goal point `current` to the start (in reversed form) 
        # containing waypoints that should be followed to get to the goal point
        full_path = deque()
        trending_path = deque()

        # The previous point, initially the goal point.
        previous = current

        # Whether we are adding the first point to the path.
        first = True

        # The new trend of the differences between the coordinates of the 
        # current and previous positions.
        d = tuple()

        # The trend of the differences between the coordinates of the previous 
        # poisition and the one before that.
        trend = (0, 0)
        while current in self._came_from:
            current = self._came_from.pop(current)

            # Track the current trend of the point differences. If it is the 
            # same kind of difference, then we may be able to skip this point 
            # in our list of waypoints.
            d = tuple(np.sign(current[i] - previous[i]) for i in [0, 1])
            alt_trend = (trend[i] != 0 and d[i] != trend[i] for i in [0, 1])
            trending = any(alt_trend)

            if self._use_indices:
                location = previous
            else:
                location = self._get_location(previous)

            full_path.appendleft(location)
            if first or trending:
                trending_path.appendleft(location)

            trend = d
            previous = current
            first = False

        return list(full_path), list(trending_path)

    def _get_cost(self, start_idx, goal_idx, turning_cost, direction=None):
        """
        Calculate the cost from traveling from a location with memory map index
        `start_idx` to a location with memory map index `goal_idx`. This
        is the bird's-eye distance between the two locations, which should be
        the "real" traveling distance for directly connected indices, plus any
        cost from turning into the correct direction, where `turning_cost` is
        a factor to scale the radians of the turns to the distance that
        a vehicle could otherwise travel in that time. Set `turning_cost` to `0`
        to remove it from the cost. `direction` is the target direction that
        the vehicle has after traveling. It is calculated from the locations if
        it is not provided.
        """

        # For geometries that support it, speed up by using the norm 
        # calculation directly for the memory map indices that directly map to 
        # evenly spread out coordinates. This saves some Location object 
        # overhead, as well as some geometry internal call overhead.
        if self._norm:
            dNorth = (goal_idx[0] - start_idx[0]) / self._resolution
            dEast = (goal_idx[1] - start_idx[1]) / self._resolution
            if turning_cost == 0.0 or np.isnan(self._d[start_idx]):
                turn = 0.0
            else:
                if direction is None:
                    direction = math.atan2(dEast, dNorth)

                turn = abs(self._geometry.diff_angle(self._d[start_idx],
                                                     direction))

            return self._norm(dNorth, dEast) + turning_cost * turn

        start = self._get_location(start_idx)
        goal = self._get_location(goal_idx)
        distance = self._geometry.get_distance_meters(start, goal)

        if turning_cost == 0.0 or np.isnan(self._d[start_idx]):
            turn = 0.0
        else:
            if direction is None:
                angle = self._geometry.get_angle(start, goal)
                direction = self._geometry.angle_to_bearing(angle)

            turn = abs(self._geometry.diff_angle(self._d[start_idx], direction))

        return distance + turning_cost * turn
