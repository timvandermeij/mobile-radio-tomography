import math
import thread
import time
from enum import IntEnum
from ..core.Threadable import Threadable

class Line_Follower_Direction(IntEnum):
    """
    Enumeration of possible directions of the line follower.

    The cardinal directions are enumerated clockwise starting from up.
    """

    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

    @classmethod
    def from_yaw(cls, heading):
        """
        Convert a yaw `heading` into a line follower direction that matches the
        yaw the closest. The `heading` is given in radians, where upward is
        zero degrees and and increments clockwise.
        """

        return cls(round(2*heading/math.pi) % 4)

    @property
    def yaw(self):
        """
        Provide the yaw heading of the current direction. The `heading` is given
        in radians, where upward is zero degrees and and increments clockwise.
        """

        return self * math.pi/2

    @property
    def axis(self):
        """
        Provide the axis of reference for the current direction.

        For up and down, the axis of reference is `0`, and for left and right
        it is `1`. For coordinate tuples that use northward and eastward axes,
        then this matches with the indexes used for such tuples.
        """

        return self % 2

    @property
    def sign(self):
        """
        Provide the sign of the current direction.

        The sign is either `-1` or `1` and determines whether the direction
        would lead to a lower coordinate value for the axis of direction.

        Thus, up and right result in `1`, while down and left result in `-1`.
        """

        return -2 * (self / 2) + 1

    def invert(self):
        """
        Retrieve the inverted value of the direction. This exchanges up and down
        or right and left.
        """

        return Line_Follower_Direction((self + 2) % 4)

    def add(self, direction):
        """
        Return the resulting direction if the current direction and the given
        `direction` are added up to each other.
        """

        return Line_Follower_Direction((self + direction) % 4)

    def get_rotate_direction(self, target_direction):
        """
        Determine the direction in which we can rotate to the given
        `target_direction`, a `Line_Follower_Direction`, the quickest.

        The returned value is `1` is clockwise rotation is the quickest, and
        `-1` if counterclockwise rotation is the quickest.
        """

        steps = (target_direction - self + 2) % 4 - 2
        return int(math.copysign(1, steps))

class Line_Follower_State(IntEnum):
    AT_LINE = 1
    AT_INTERSECTION = 2

class Line_Follower_Bit_Mask(IntEnum):
    LINE = 0b0110
    LINE_LEFT = 0b1000
    LINE_RIGHT = 0b0001
    INTERSECTION = 0b1001

class Line_Follower(Threadable):
    def __init__(self, location, direction, callback, thread_manager, delay=0):
        """
        Initialize the line follower object. We assume that we are working
        with the Zumo Robot for Arduino v1.2 (assembled with 75:1 HP motors),
        which has a line follower with six LEDs.
        """

        super(Line_Follower, self).__init__("line_follower", thread_manager)

        if not isinstance(location, tuple):
            raise ValueError("Location must be a tuple")

        self._location = location
        self.set_direction(direction)
        self._callback = callback
        self._state = Line_Follower_State.AT_LINE

        self._delay = delay
        self._running = False

    def _loop(self):
        try:
            while self._running:
                self.enable()
                sensor_values = self.read()
                # Check whether the thread has stopped in between, since the 
                # read method may take long.
                if not self._running:
                    return

                self.update(sensor_values)
                self.disable()
                time.sleep(self._delay)
        except:
            super(Line_Follower, self).interrupt()

    def activate(self):
        super(Line_Follower, self).activate()
        self._running = True
        thread.start_new_thread(self._loop, ())

    def deactivate(self):
        super(Line_Follower, self).deactivate()
        self._running = False

    def enable(self):
        raise NotImplementedError("Subclasses must implement enable()")

    def disable(self):
        raise NotImplementedError("Subclasses must implement disable()")

    def read(self):
        raise NotImplementedError("Subclasses must implement read()")

    def update(self, sensor_values):
        """
        Update the state and location of the vehicle by interpreting the
        sensor values from the line follower.
        """

        if not isinstance(sensor_values, list) or len(sensor_values) != 4:
            raise ValueError("Sensor values must be a list with four elements")

        # Represent the state as an integer to allow for bit manipulations.
        state = 0
        for sensor_value in sensor_values:
            state = state << 1
            state += sensor_value

        # Check if we are at a line or at an intersection and update the
        # state and location of the vehicle accordingly.
        line = state & Line_Follower_Bit_Mask.LINE
        intersection = state & Line_Follower_Bit_Mask.INTERSECTION
        if line and not intersection:
            self._state = Line_Follower_State.AT_LINE
        elif line and intersection:
            if self._state == Line_Follower_State.AT_INTERSECTION:
                # Do not keep updating the location when the vehicle is
                # waiting at an intersection.
                return

            self._state = Line_Follower_State.AT_INTERSECTION

            # Update the location using the direction.
            if self._direction == Line_Follower_Direction.UP:
                self._location = (self._location[0], self._location[1] + 1)
            elif self._direction == Line_Follower_Direction.DOWN:
                self._location = (self._location[0], self._location[1] - 1)
            elif self._direction == Line_Follower_Direction.LEFT:
                self._location = (self._location[0] - 1, self._location[1])
            elif self._direction == Line_Follower_Direction.RIGHT:
                self._location = (self._location[0] + 1, self._location[1])

            # Notify the listener (callback) and pass the new location.
            self._callback("intersection", self._location)
        elif not line and intersection:
            # The rover has diverged from the grid. Determine where the
            # line on the grid is (left or right) so the rover controller
            # can correct its path. If we detect a line on the left and
            # on the right, we do nothing as we do not know where to
            # correct the path to. The same holds for the situation where
            # we do not detect any lines, which is why the else clause
            # is missing below.
            if intersection == Line_Follower_Bit_Mask.INTERSECTION:
                return

            is_line_left = (intersection == Line_Follower_Bit_Mask.LINE_LEFT)
            self._callback("diverged", "left" if is_line_left else "right")

    def set_state(self, state):
        """
        Set the state of the line follower.
        """

        if not isinstance(state, int) or not 1 <= state <= 2:
            raise ValueError("Direction must be one of the defined types")

        self._state = state

    def set_direction(self, direction):
        """
        Set the direction of the vehicle.
        """

        if not isinstance(direction, int) or not 0 <= direction <= 3:
            raise ValueError("Direction must be one of the defined types")

        self._direction = direction
