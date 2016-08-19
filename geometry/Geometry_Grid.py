import numpy as np
from Geometry import Geometry

class Geometry_Grid(Geometry):
    """
    Geometry that operates in a grid-like environment where one can only move
    north, east, south or west in discrete steps.
    """

    _norm = lambda self, dx, dy, dz=0: abs(dx) + abs(dy) + abs(dz)

    def _get_range(self, start_coord, end_coord, count):
        R = super(Geometry_Grid, self)._get_range(start_coord, end_coord, count)

        # Ensure the range contains only grid coordinates
        return np.round(R)

    def get_neighbor_offsets(self):
        # pylint: disable=bad-continuation,bad-whitespace
        return np.array([          (-1, 0),
                          (0, -1),           (0, 1),
                                    (1, 0)          ])
