from dronekit import LocationLocal
from Mission_Infrared import Mission_Infrared

class Mission_Infrared_Grid(Mission_Infrared):
    """
    A mission that drives around with a `Robot_Vehicle` on a line following grid
    based on button presses that are read using the `Infrared_Sensor`.
    """

    def setup(self):
        super(Mission_Infrared_Grid, self).setup()
        self._diff = [0, 0]

    def _release(self):
        if self._diff[0] == 0 and self._diff[1] == 0:
            return

        location = self.vehicle.location
        new_location = LocationLocal(location.north + self._diff[0], location.east + self._diff[1], -self.altitude)
        self.vehicle.simple_goto(new_location)
        self._diff = [0, 0]

    def _up(self):
        self._diff[0] = 1

    def _down(self):
        self._diff[0] = -1

    def _left(self):
        self._diff[1] = -1

    def _right(self):
        self._diff[1] = 1
