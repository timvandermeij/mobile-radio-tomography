import itertools
from collections import deque
from dronekit import LocationLocal
from Mission_Auto import Mission_Auto
from ..vehicle.Robot_Vehicle import Robot_Vehicle

class Mission_Calibrate(Mission_Auto):
    """
    A mission that performs calibration measurements on a grid (i.e. all the
    measurements links that are possible) using a `Robot_Vehicle`.
    """

    def _get_round(self):
        vehicle_round = list(self.chain)[1:-1]
        self.chain.rotate(1)
        return vehicle_round

    def setup(self):
        super(Mission_Calibrate, self).setup()

        if not isinstance(self.vehicle, Robot_Vehicle):
            raise ValueError("Mission_Calibrate only works with robot vehicles")

        wpzip = itertools.izip_longest
        grid_size = int(self.size)
        # Last coordinate index of the grid in both directions
        size = grid_size - 1

        self.chain = deque(itertools.chain(
            wpzip(xrange(0, size), [], fillvalue=0),
            wpzip([], xrange(0, size), fillvalue=size),
            wpzip(xrange(size, 0, -1), [], fillvalue=size),
            wpzip([], xrange(size, 0, -1), fillvalue=0)
        ))
        self.waypoints = []

        location = self.vehicle.location
        start_point = (int(location.north), int(location.east))

        if location.north == 0 and location.east == 0:
            self.id = 0
        elif location.north == 0 and location.east == 1:
            self.id = 1
        else:
            raise ValueError("Vehicle is incorrectly positioned at ({},{}), must be at (0,0) or (0,1)".format(location.north, location.east))

        last_point = None
        last_own_point = start_point
        self.round_number = 0
        while last_point != (0, 1):
            vehicle_round = self._get_round()
            last_point = vehicle_round[-1]
            if self.round_number % 2 == self.id:
                self.waypoints.extend(vehicle_round)
                last_own_point = last_point
            else:
                self.waypoints.extend([last_own_point] * len(vehicle_round))

            self.round_number += 1

    def get_points(self):
        return [
            LocationLocal(north, east, 0.0) for north, east in self.waypoints
        ]
