import numpy as np
from ..geometry.Geometry_Grid import Geometry_Grid

class AStar(object):
    """
    An A* search algorithm that works on a grid-like memory map containing free
    paths and detected objects.
    """

    def __init__(self, geometry, memory_map, allow_at_bounds=False,
                 trend_strides=True, use_indices=False):
        """
        Initialize the A* search algorithm. The given `geometry` is a `Geometry`
        object for the space, and `memory_map` is a `Memory_Map` for the part of
        the space that the vehicle operates in.

        If `allow_at_bounds` is `True`, then the boundary of the memory map is
        acceptable for the vehicle to be situated in, otherwise these locations
        are skipped when creating a path to the location. Setting this to `True`
        is useful for robot vehicles that operate on a fixed-size grid.

        `trend_strides` determines whether we should return a reconstructed path
        where intermediate locations that follow the same trend as the one
        before them, are skipped. This can be set to `False` to obtain the full
        path every time. If `use_indices` is `True`, then memory map indices are
        reconstructed instead of Location objects.
        """

        self._geometry = geometry
        self._memory_map = memory_map

        self._allow_at_bounds = allow_at_bounds
        self._trend_strides = trend_strides
        self._use_indices = use_indices

        self._neighbors = self._geometry.get_neighbor_offsets()
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

    def _get_close_map(self, closeness):
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
        if idx not in self._locations:
            self._locations[idx] = self._memory_map.get_location(*idx)

        return self._locations[idx]

    def assign(self, start, goal, closeness):
        """
        Perform the A* search algorithm to create a list of waypoints that bring
        the vehicle from the Location `start` to the Location `goal` while not
        going through objects or getting closer than `closeness` meters to them.

        When a safe and fast path is found, then it returns the list of
        Locations that describe path waypoints and the distance cost.

        If no such assignment can be found, then an empty list and infinity is
        returned.
        """

        start_idx = self._memory_map.get_index(start)
        goal_idx = self._memory_map.get_index(goal)

        self._locations[start_idx] = start
        self._locations[goal_idx] = goal

        close = self._get_close_map(closeness)

        if start_idx == goal_idx:
            # Already at the requested location, simply return it as the 
            # waypoint even if this location is unsafe (since stoppping is 
            # considered a safe action).
            return [goal_idx if self._use_indices else goal], 0.0

        if not self._memory_map.index_in_bounds(*goal_idx) or close[goal_idx]:
            # No safe path to the location since the location is unsafe, due to 
            # it being outside of the memory map or too close to an object.
            return [], np.inf

        # If we are allowed to move on the bounds of the memory map, but not 
        # outside it, then we can speed up the out of bounds check by 
        # considering these indices as evaluated. Thus they are skipped without 
        # having a memory map call overhead.
        if self._allow_at_bounds:
            evaluated = self._out_of_bounds.copy()
        else:
            evaluated = set()

        open_nodes = set([start_idx])
        came_from = {}

        # Cost along best known path
        g = np.full((self._size, self._size), np.inf)
        g[start_idx] = 0.0

        # Estimated total cost from start to goal when passing through 
        # a specific index.
        f = np.full((self._size, self._size), np.inf)
        f[start_idx] = self._get_cost(start_idx, goal_idx)

        while open_nodes:
            # Get the node in open_nodes with the lowest f score
            open_indices = zip(*open_nodes)
            min_idx = np.argmin(f[open_indices])
            current_idx = (open_indices[0][min_idx], open_indices[1][min_idx])

            # If we reached the goal index, then we have found the fastest 
            # safest path to it, thus reconstruct this path.
            if current_idx == goal_idx:
                return self._reconstruct(came_from, goal_idx), g[goal_idx]

            # Evaluate the new node
            open_nodes.remove(current_idx)
            evaluated.add(current_idx)
            for neighbor_coord in current_idx + self._neighbors:
                # Create the neighbor index and check whether we have evaluated 
                # it before.
                neighbor_idx = tuple(neighbor_coord)
                if neighbor_idx in evaluated:
                    continue

                # Check whether the neighbor index is still in bounds. We can 
                # break if it is not in bounds, because that means that the 
                # current location is close to the memory map bounds, which 
                # could be considered unsafe. But if we have the possibility to 
                # move at the boundary, then try the next neighbor instead.
                if not self._allow_at_bounds:
                    if not self._memory_map.index_in_bounds(*neighbor_idx):
                        break

                # Check whether the neighbor index is inside the region of 
                # influence of any other object.
                if close[neighbor_idx]:
                    continue

                # Calculate the new tentative distances to the point
                tentative_g = g[current_idx] + self._get_cost(current_idx, neighbor_idx)
                if tentative_g >= g[neighbor_idx]:
                    # Not a better path, thus we do not need to update anything 
                    # for this neighbor which has a different, faster path.
                    continue

                open_nodes.add(neighbor_idx)
                came_from[neighbor_idx] = current_idx
                g[neighbor_idx] = tentative_g
                f[neighbor_idx] = tentative_g + self._get_cost(neighbor_idx, goal_idx)

        return [], np.inf

    def _reconstruct(self, came_from, current):
        # The path from goal point `current` to the start (in reversed form) 
        # containing waypoints that should be followed to get to the goal point
        total_path = []
        previous = current
        first = True
        d = tuple()

        # The current trend of the differences between the points
        trend = (0, 0)
        while current in came_from:
            current = came_from.pop(current)

            # Track the current trend of the point differences. If it is the 
            # same kind of difference, then we may be able to skip this point 
            # in our list of waypoints.
            if self._trend_strides:
                d = tuple(np.sign(current[i] - previous[i]) for i in [0, 1])
                alt_trend = (trend[i] != 0 and d[i] != trend[i] for i in [0, 1])
                trending = any(alt_trend)
            else:
                trending = True

            if first or trending:
                if self._use_indices:
                    total_path.append(previous)
                else:
                    total_path.append(self._get_location(previous))

            trend = d
            previous = current
            first = False

        return list(reversed(total_path))

    def _get_cost(self, start_idx, goal_idx):
        # For grid geometry, speed up by using our own norm calculation. This 
        # saves some call and Location object overhead.
        if isinstance(self._geometry, Geometry_Grid):
            return abs(start_idx[0] - goal_idx[0] + start_idx[1] - goal_idx[1])

        start = self._get_location(start_idx)
        goal = self._get_location(goal_idx)
        return self._geometry.get_distance_meters(start, goal)
