import numpy as np

class AStar(object):
    """
    An A* search algorithm that works on a grid-like memory map containing free
    paths and detected objects.
    """

    def __init__(self, geometry, memory_map, allow_at_bounds=False):
        self._geometry = geometry
        self._memory_map = memory_map

        self._allow_at_bounds = allow_at_bounds

        self._neighbors = self._geometry.get_neighbor_offsets()
        self._resolution = float(self._memory_map.get_resolution())
        self._size = self._memory_map.get_size()

    def assign(self, start, goal, closeness):
        """
        Perform the A* search algorithm to create a list of waypoints that bring
        the vehicle from the Location `start` to the Location `goal` while not
        going through objects or getting closer than `closeness` meters to them.

        If no such assignment can be found, then an empty list is returned.
        """

        start_idx = self._memory_map.get_index(start)
        goal_idx = self._memory_map.get_index(goal)

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

        evaluated = set()
        open_nodes = set([start_idx])
        came_from = {}

        # Cost along best known path
        g = np.full((self._size, self._size), np.inf)
        g[start_idx] = 0.0

        # Estimated total cost from start to goal when passing through 
        # a specific index.
        f = np.full((self._size, self._size), np.inf)
        f[start_idx] = self._get_cost(start, goal)

        while open_nodes:
            # Get the node in open_nodes with the lowest f score
            open_indices = zip(*open_nodes)
            min_idx = np.argmin(f[open_indices])
            current_idx = (open_indices[0][min_idx], open_indices[1][min_idx])

            # If we reached the goal index, then we have found the fastest 
            # safest path to it, thus reconstruct this path.
            if current_idx == goal_idx:
                return self._reconstruct(came_from, goal_idx)

            # Evaluate the new node
            open_nodes.remove(current_idx)
            evaluated.add(current_idx)
            current = self._memory_map.get_location(*current_idx)
            for neighbor_coord in self._get_neighbors(current_idx):
                # Create the neighbor index and check whether we have evaluated 
                # it before.
                neighbor_idx = tuple(neighbor_coord)
                if neighbor_idx in evaluated:
                    continue

                # Check whether the neighbor index is still in bounds. We can 
                # break if it is not in bounds, because that means that the 
                # current location is close to the memory map bounds, which 
                # could be considered unsafe. But if we want to have to 
                # possibility to move at the boundary, then continue instead.
                if not self._memory_map.index_in_bounds(*neighbor_idx):
                    if self._allow_at_bounds:
                        continue
                    else:
                        break

                # Check whether the neighbor index is inside the region of 
                # influence of any other object.
                if close[neighbor_idx]:
                    continue

                # Calculate the new tentative distances to the point
                neighbor = self._memory_map.get_location(*neighbor_idx)
                tentative_g = g[current_idx] + self._get_cost(current, neighbor)
                if tentative_g >= g[neighbor_idx]:
                    # Not a better path, thus we do not need to update anything 
                    # for this neighbor which has a different, faster path.
                    continue

                open_nodes.add(neighbor_idx)
                came_from[neighbor_idx] = current_idx
                g[neighbor_idx] = tentative_g
                f[neighbor_idx] = tentative_g + self._get_cost(neighbor, goal)

        return []

    def _reconstruct(self, came_from, current):
        # The path from goal point `current` to the start (in reversed form) 
        # containing waypoints that should be followed to get to the goal point
        total_path = []
        previous = current

        # The current trend of the differences between the points
        trend = None
        while current in came_from:
            current = came_from.pop(current)

            # Track the current trend of the point differences. If it is the 
            # same kind of difference, then we may be able to skip this point 
            # in our list of waypoints.
            d = tuple(np.sign(current[i] - previous[i]) for i in [0,1])
            if trend is None or (trend[0] != 0 and d[0] != trend[0]) or (trend[1] != 0 and d[1] != trend[1]):
                trend = d
                total_path.append(self._memory_map.get_location(*previous))
            else:
                trend = d

            previous = current

        return list(reversed(total_path))

    def _get_neighbors(self, current):
        return current + self._neighbors

    def _get_cost(self, start, goal):
        return self._geometry.get_distance_meters(start, goal)
