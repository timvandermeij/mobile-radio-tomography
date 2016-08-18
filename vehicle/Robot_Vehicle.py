# Core imports
import math
import thread
import time

# Library imports
from dronekit import LocationLocal, Attitude, VehicleMode
import numpy as np

# Package imports
from Vehicle import Vehicle
from ..core.WiringPi import WiringPi
from ..location.Line_Follower import Line_Follower, Line_Follower_Direction, Line_Follower_State

class Robot_State(object):
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

class Robot_State_Rotate(Robot_State):
    def __init__(self, rotate_direction, target_direction, current_direction):
        super(Robot_State_Rotate, self).__init__("rotate")
        # Direction in which we are rotating (-1 is left, 1 is right)
        self.rotate_direction = rotate_direction
        # Target direction (Line_Follower_Direction enum)
        self.target_direction = target_direction
        # The current direction (Line_Follower_Direction enum)
        self.current_direction = current_direction

class Robot_Vehicle(Vehicle):
    """
    Base class for vehicles that work (semi)directly with a line following robot
    to determine its location and state.
    """

    _line_follower_class = None

    def __init__(self, arguments, geometry, import_manager, thread_manager, usb_manager):
        super(Robot_Vehicle, self).__init__(arguments, geometry,
                                            import_manager, thread_manager,
                                            usb_manager)

        self.arguments = arguments
        self.settings = self.arguments.get_settings("vehicle_robot")

        self._move_speed = 0.0

        # Speed ratio of the current move speed when we diverge from a line.
        self._diverged_speed = self.settings.get("diverged_speed")
        # Time in seconds to keep adjusted speed when we diverge from a line.
        self._diverged_time = self.settings.get("diverged_time")
        self._last_diverged_time = None

        # Speed in m/s to use when we rotate on an intersection.
        self._rotate_speed = self.settings.get("rotate_speed")

        # The home location coordinates of the robot. The robot should be 
        # placed at the intersection corresponding to these coordinates to 
        # begin with.
        self._home_location = tuple(self.settings.get("home_location"))
        self._location = self._home_location
        # The starting direction of the robot. The robot should be aligned with 
        # this direction to begin with.
        self._direction = self.settings.get("home_direction")

        self._line_follower = None
        self._setup_line_follower(import_manager, thread_manager, usb_manager)

        # The delay of the robot vehicle state loop.
        self._loop_delay = self.settings.get("vehicle_delay")

        self._waypoints = []
        self._current_waypoint = -1

        # Current state of the robot. Possible states include:
        # - "intersection": The robot is standing still at an intersection.
        # - "rotate": The robot is rotating at an intersection. See
        #   `Robot_State_Rotate` for additional fields.
        # - "move": The robot is moving toward a specific waypoint and not
        #   rotating. This state may be interrupted by an "intersection" state, 
        #   which causes the `_check_state` loop determine whether it has 
        #   reached the waypoint or that it should continue moving.
        # Subclasses may add more internal states for additional functionality.
        self._state = Robot_State("intersection")

        # Whether the vehicle is temporarily halted, i.e., it is set in the 
        # "HALT" mode. When it is and the mode is changed to something other 
        # than "HALT", then the vehicle is automatically reactivated.
        self._halted = False
        self._old_mode = self._mode

        self._servo_pins = set()

        self.notify_attribute_listeners("home_location", self.home_location)

    def setup(self):
        super(Robot_Vehicle, self).setup()

        self._wiringpi = WiringPi()

    def _setup_line_follower(self, import_manager, thread_manager, usb_manager):
        if self._line_follower_class is None:
            raise NotImplementedError("Subclasses must provide a `_line_follower_class` property")

        line_follower_class = import_manager.load_class(self._line_follower_class,
                                                        relative_module="location")

        if not issubclass(line_follower_class, Line_Follower):
            raise TypeError("`_line_follower_class` must be a `Line_Follower` class")

        # The delay of the sensor reading loop in the line follower thread.
        line_follower_delay = self.settings.get("line_follower_delay")
        self._line_follower = line_follower_class(
            self._home_location, self._direction,
            self.line_follower_callback, self.arguments,
            thread_manager, usb_manager=usb_manager, delay=line_follower_delay
        )
        self._line_follower.set_state(Line_Follower_State.AT_INTERSECTION)

    def _state_loop(self):
        try:
            while self._armed:
                self._check_state()
                time.sleep(self._loop_delay)
        except:
            super(Robot_Vehicle, self).interrupt()

    def _check_state(self):
        if isinstance(self._state, Robot_State_Rotate):
            if self._state.current_direction == self._state.target_direction:
                # When we are done rotating, stand still again before 
                # determining our next moves.
                self._direction = self._state.current_direction
                self._state = Robot_State("intersection")
                self.set_speeds(0, 0)
                self._line_follower.set_direction(self._direction)
        elif self._state.name == "move":
            if self._last_diverged_time is not None:
                diff = time.time() - self._last_diverged_time
                if diff >= self._diverged_time:
                    self.set_speeds(self.speed, self.speed)
                    self._last_diverged_time = None
        else:
            self._check_intersection()

    def _check_intersection(self):
        if self._state.name == "intersection":
            if self._at_current_waypoint():
                # We reached the current waypoint.
                if self._mode.name == "AUTO":
                    # In AUTO mode, immediately try to move to the next 
                    # waypoint, or rotate in the right direction.
                    self._move_waypoint(self._current_waypoint + 1)
                else:
                    # In other modes, stop at the current waypoint until we 
                    # have a new waypoint.
                    self.set_speeds(0, 0)
            elif self._mode.name == "AUTO" or self._mode.name == "GUIDED":
                # We reached an intersection or we are at an intersection and 
                # maybe have a next waypoint. Check whether we need to rotate 
                # here, and otherwise move away from it to the next waypoint.
                self._move_waypoint(max(0, self._current_waypoint))

    def line_follower_callback(self, event, data):
        if event == "intersection":
            # Invert location data since the Line_Follower is in (x,y) notation 
            # where y is north and x is east.
            self._location = (data[1], data[0])
            self._state = Robot_State(event)
        elif event == "diverged":
            direction = -1 if data == "left" else 1
            if isinstance(self._state, Robot_State_Rotate):
                # Keep line follower in intersection state while the vehicle 
                # rotates on an intersection.
                self._line_follower.set_state(Line_Follower_State.AT_INTERSECTION)
                if direction == self._state.rotate_direction:
                    # We are rotating on an intersection to move to our next 
                    # direction, thus track whether we found a new line. Only 
                    # do so when we see the line from the side that we are 
                    # moving to, not when we rotate away from it again.
                    direction = (self._state.current_direction + direction) % 4
                    new_state = Robot_State_Rotate(self._state.rotate_direction,
                                                   self._state.target_direction,
                                                   direction)
                    self._state = new_state
            elif self._is_waypoint(self._current_waypoint):
                # We went off the line while moving (semi)automatically to 
                # a next waypoint. Steer the motors such that the robot gets 
                # back to the line.
                speed = self._move_speed
                speed_difference = direction * self._diverged_speed * speed
                self.set_speeds(speed + speed_difference,
                                speed - speed_difference)
                self._last_diverged_time = time.time()

    def set_speeds(self, left_speed, right_speed, left_forward=True,
                   right_forward=True):
        raise NotImplementedError("Subclasses must implement `set_speeds` method")

    @property
    def use_simulation(self):
        # We do not support simulation (physical environments only)
        return False

    @property
    def home_location(self):
        return self._geometry.make_location(*self._home_location)

    @home_location.setter
    def home_location(self, value):
        self._home_location = self._geometry.get_coordinates(value)[:2]
        self.notify_attribute_listeners("home_location", self.home_location)

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        if value.name == "HALT":
            self.pause()
        elif self._halted:
            self.unpause()

        if value.name == "RTL":
            self._waypoints = [self._home_location]
            self._current_waypoint = -1

    @property
    def armed(self):
        return self._armed and not self._halted

    @armed.setter
    def armed(self, value):
        if value:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        super(Robot_Vehicle, self).activate()

        if self._armed:
            return

        if self._line_follower is not None:
            self._line_follower.activate()

        self._armed = True
        thread.start_new_thread(self._state_loop, ())

    def deactivate(self):
        super(Robot_Vehicle, self).deactivate()

        if self._armed:
            self._armed = False
            if self._line_follower is not None:
                self._line_follower.deactivate()

    def pause(self):
        self._old_mode = self._mode
        self._mode = VehicleMode("HALT")
        self._halted = True

    def unpause(self):
        """
        Unpause the vehicle from its halted mode.
        """

        if not self._halted:
            raise RuntimeError("Can only unpause a halted vehicle")

        self._halted = False
        if self._mode.name == "HALT":
            self.mode = self._old_mode

    def add_waypoint(self, location):
        self._waypoints.append(self._geometry.get_coordinates(location)[:2])

    def add_wait(self):
        self._waypoints.append(None)

    def is_wait(self):
        if not self._is_waypoint(self._current_waypoint):
            return False

        return self._waypoints[self._current_waypoint] is None

    def clear_waypoints(self):
        self._waypoints = []

    def get_waypoint(self, waypoint=-1):
        if waypoint == -1:
            waypoint = self._current_waypoint

        if not self._is_waypoint(waypoint):
            return None

        wp = self._waypoints[waypoint]
        if wp is None:
            return None

        return LocationLocal(wp[0], wp[1], 0.0)

    def get_next_waypoint(self):
        return self._current_waypoint

    def set_next_waypoint(self, waypoint=-1):
        if waypoint == -1:
            waypoint = self._current_waypoint + 1

        self._current_waypoint = waypoint

    def count_waypoints(self):
        return len(self._waypoints)

    def simple_goto(self, location):
        self._waypoints = []
        self._current_waypoint = -1
        self.add_waypoint(location)

    def is_current_location_valid(self):
        # When we are moving, then the location is no longer correct.
        if self._is_moving():
            return False

        # If we are not at the waypoint and not waiting there based on 
        # a command, then the location is not yet valid.
        if not self._at_current_waypoint() and not self.is_wait():
            return False

        return super(Robot_Vehicle, self).is_current_location_valid()

    @property
    def location(self):
        return LocationLocal(self._location[0], self._location[1], 0.0)

    @property
    def speed(self):
        return self._move_speed

    @speed.setter
    def speed(self, value):
        forward = True
        if value < 0:
            forward = False
            value = -value

        self._move_speed = value
        if self._is_moving() and self._last_diverged_time is None:
            self.set_speeds(value, value,
                            left_forward=forward, right_forward=forward)

    @property
    def velocity(self):
        direction = self._get_current_direction()
        speeds = [0.0, 0.0, 0.0]

        if direction == Line_Follower_Direction.UP:
            speeds[0] = self._move_speed
        elif direction == Line_Follower_Direction.RIGHT:
            speeds[1] = self._move_speed
        elif direction == Line_Follower_Direction.DOWN:
            speeds[0] = -self._move_speed
        elif direction == Line_Follower_Direction.LEFT:
            speeds[1] = -self._move_speed
        else:
            raise ValueError("Invalid direction '{}'".format(direction))

        return speeds

    @velocity.setter
    def velocity(self, value):
        nonzero = np.nonzero(value[:2])[0]
        if nonzero.size == 0:
            self.speed = 0.0
        elif nonzero.size == 1:
            self.speed = value[nonzero[0]]
        else:
            raise ValueError("At most one speed component can be nonzero for robot vehicle")

    def _get_current_direction(self):
        if isinstance(self._state, Robot_State_Rotate):
            return self._state.current_direction

        return self._direction

    def _get_yaw(self):
        direction = self._get_current_direction()

        if direction == Line_Follower_Direction.UP:
            yaw = 0.0
        elif direction == Line_Follower_Direction.RIGHT:
            yaw = 0.5 * math.pi
        elif direction == Line_Follower_Direction.DOWN:
            yaw = math.pi
        elif direction == Line_Follower_Direction.LEFT:
            yaw = 1.5 * math.pi
        else:
            raise ValueError("Invalid direction '{}'".format(direction))

        return yaw

    @property
    def attitude(self):
        yaw = self._get_yaw()

        return Attitude(0.0, yaw, 0.0)

    def set_yaw(self, heading, relative=False, direction=1):
        if not self._at_intersection():
            # We can only rotate on an intersection where we can see all 
            # cardinal lines.
            return

        if relative:
            heading = self._get_yaw() + heading

        target_direction = int(round(2*heading/math.pi)) % 4

        self._set_direction(target_direction, direction)

    def _get_rotate_direction(self, target_direction):
        """
        Determine the direction in which the vehicle rotates to the given
        `target_direction`, a `Line_Follower_Direction`, the quickest.

        The returned value is `1` is clockwise rotation is the quickest, and
        `-1` if counterclockwise rotation is the quickest.
        """

        steps = (target_direction - self._direction + 2) % 4 - 2
        return int(math.copysign(1, steps))

    def _set_direction(self, target_direction, rotate_direction=0):
        if target_direction == self._direction:
            return

        if rotate_direction == 0:
            # Determine direction in which we rotate to the target direction 
            # the quickest.
            rotate_direction = self._get_rotate_direction(target_direction)

        self._state = Robot_State_Rotate(rotate_direction, target_direction,
                                         self._direction)

        # Keep line follower in intersection state.
        self._line_follower.set_state(Line_Follower_State.AT_INTERSECTION)

        # Start turning the vehicle at turning speed. If we want to rotate 
        # clockwise, the left motor goes forward and the right motor backward, 
        # while counterclockwise is the other way around.
        self.set_rotate(rotate_direction)

    def set_rotate(self, rotate_direction):
        self.set_speeds(self._rotate_speed, self._rotate_speed,
                        left_forward=rotate_direction == 1,
                        right_forward=rotate_direction == -1)

    def _is_waypoint(self, waypoint):
        return 0 <= waypoint < len(self._waypoints)

    def _move_waypoint(self, waypoint):
        """
        Attempt to move to the given `waypoint`. The `waypoint` should usually
        be the next or current waypoint, depending on whether we reached the
        current waypoint or not.
        This method must only be called if we are at an intersection that is
        equal to the current waypoint location.
        """

        if not self._is_waypoint(waypoint):
            # If there is no new waypoint, do nothing and stand still if we 
            # happened to reach the current waypoint
            if self._is_waypoint(self._current_waypoint):
                self.set_speeds(0, 0)

            return

        if self._goto_waypoint(self._waypoints[waypoint]):
            self._current_waypoint = waypoint

    def _goto_waypoint(self, next_waypoint):
        if next_waypoint is None:
            return True

        next_direction = self._next_direction(next_waypoint)
        if next_direction == self._direction:
            # Start moving in the given direction
            self._state = Robot_State("move")
            self.set_speeds(self.speed, self.speed)
            return True
        else:
            # Move to the correct direction, which is not yet part of moving to 
            # the waypoint.
            self._set_direction(next_direction)
            return False

    def _next_direction(self, waypoint):
        up = waypoint[0] - self._location[0]
        right = waypoint[1] - self._location[1]

        is_up = self._direction == Line_Follower_Direction.UP
        is_right = self._direction == Line_Follower_Direction.RIGHT
        is_down = self._direction == Line_Follower_Direction.DOWN
        is_left = self._direction == Line_Follower_Direction.LEFT

        if (is_up and up > 0) or (is_right and right > 0) or (is_down and up < 0) or (is_left and right < 0):
            return self._direction

        if right == 0 or is_right or is_left:
            if up > 0:
                return Line_Follower_Direction.UP
            if up < 0:
                return Line_Follower_Direction.DOWN
        else:
            if right > 0:
                return Line_Follower_Direction.RIGHT
            if right < 0:
                return Line_Follower_Direction.LEFT

        # No need to change direction if the difference is 0 for both cardinal 
        # directions.
        return self._direction

    def _is_moving(self):
        return self.armed and self._state.name == "move"

    def _at_intersection(self):
        if self._state.name == "intersection":
            return True

        return isinstance(self._state, Robot_State_Rotate)

    def _at_current_waypoint(self):
        if not self._is_waypoint(self._current_waypoint):
            return False

        waypoint = self._waypoints[self._current_waypoint]
        return waypoint == self._location

    def set_servo(self, servo, pwm):
        if self._wiringpi.is_raspberry_pi:
            if servo.pin not in self._servo_pins:
                self._servo_pins.add(servo.pin)
                self._wiringpi.module.softPwmCreate(servo.pin, pwm, servo.pwm.max)

            self._wiringpi.module.softPwmWrite(servo.pin, pwm)

        servo.set_current_pwm(pwm)
