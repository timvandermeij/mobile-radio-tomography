from ..vehicle.Robot_Vehicle import Robot_Vehicle
from Mission_Guided import Mission_Guided

class Mission_Infrared(Mission_Guided):
    """
    A mission that drives around with a `Robot_Vehicle` based on button presses
    that are read using the `Infrared_Sensor`.
    """

    def setup(self):
        super(Mission_Infrared, self).setup()

        if not isinstance(self.vehicle, Robot_Vehicle):
            raise ValueError("Mission_Infrared only works with robot vehicles")

        self.infrared_sensor = self.environment.get_infrared_sensor()
        if self.infrared_sensor is None:
            raise ValueError("Mission_Infrared only works with infrared sensor")

    def start(self):
        super(Mission_Infrared, self).start()

        self.infrared_sensor.register("up", self._up, self._release)
        self.infrared_sensor.register("down", self._down, self._release)
        self.infrared_sensor.register("left", self._left, self._release)
        self.infrared_sensor.register("right", self._right, self._release)

    def _release(self):
        self.vehicle.set_speeds(0, 0, True, True)

    def _up(self):
        self.vehicle.set_speeds(self.speed, self.speed, True, True)

    def _down(self):
        self.vehicle.set_speeds(self.speed, self.speed, False, False)

    def _left(self):
        self.vehicle.set_rotate(-1)

    def _right(self):
        self.vehicle.set_rotate(1)
