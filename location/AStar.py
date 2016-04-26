import math
import numpy as np

class AStar(object):
    """
    An A* search algorithm that works on a grid-like memory map containing free
    paths and detected objects.
    """

    def __init__(self, geometry, memory_map):
        self._geometry = geometry
        self._memory_map = memory_map
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
        nonzero = self._memory_map.get_nonzero()

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
            open_idx = [idx for idx in open_nodes]
            min_idx = np.argmin(f[[idx[0] for idx in open_idx], [idx[1] for idx in open_idx]])
            current_idx = open_idx[min_idx]
            if current_idx == goal_idx:
                return self._reconstruct(came_from, goal_idx)

            open_nodes.remove(current_idx)
            evaluated.add(current_idx)
            current = self._memory_map.get_location(*current_idx)
            for neighbor_idx in self._get_neighbors(current_idx):
                if neighbor_idx in evaluated:
                    continue

                try:
                    if self._memory_map.get(neighbor_idx) == 1:
                        continue
                except KeyError:
                    break

                if self._is_too_close(neighbor_idx, nonzero, closeness):
                    continue

                neighbor = self._memory_map.get_location(*neighbor_idx)
                tentative_g = g[current_idx] + self._get_cost(current, neighbor)
                open_nodes.add(neighbor_idx)
                if tentative_g >= g[neighbor_idx]:
                    # Not a better path
                    continue

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
        y, x = current
        return [(y-1, x-1), (y-1, x), (y-1, x+1),
                (y, x-1),             (y, x+1),
                (y+1, x-1), (y+1, x), (y+1, x+1)]

    def _is_too_close(self, current, nonzero, closeness):
        for idx in nonzero:
            # Calculate the distance between the nonzero indices in the memory 
            # map. Speed up by doing locally.
            dist = math.sqrt(((current[0] - idx[0])/self._resolution)**2 + ((current[1] - idx[1])/self._resolution)**2)
            if dist < closeness:
                return True

        return False

    def _get_cost(self, start, goal):
        return self._geometry.get_distance_meters(start, goal)
