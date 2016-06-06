import numpy as np
from Geometry import Geometry

class Geometry_Grid(Geometry):
    """
    Geometry that operates in a grid-like environment where one can only move
    north, east, south or west in discrete steps.
    """

    def get_distance_meters(self, location1, location2):
        location1, location2 = self.equalize(location1, location2)
        diff = self._diff_location(location1, location2)
        return abs(diff.north) + abs(diff.east) + abs(diff.down)

    def get_neighbor_offsets(self):
        # pylint: disable=bad-continuation,bad-whitespace
        return np.array([          (-1, 0),
                          (0, -1),           (0, 1),
                                    (1, 0)          ])
