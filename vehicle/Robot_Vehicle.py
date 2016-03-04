from dronekit import LocationLocal, LocationGlobal, Attitude
from Vehicle import Vehicle
from ..location.Line_Follower import Line_Follower_Direction, Line_Follower_State

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

    def __init__(self, arguments, geometry):
        super(Robot_Vehicle, self).__init__(arguments, geometry)

        settings = arguments.get_settings("vehicle_robot")

        # Speed difference in m/s to adjust when we diverge from a line.
        self._diverged_speed = settings.get("diverged_speed")
        # Time in seconds to keep adjusted speed when we diverge from a line.
        self._diverged_time = settings.get("diverged_time")
        self._last_diverged_time = None

        # Speed in m/s to use when we rotate on an intersection.
        self._rotate_speed = settings.get("rotate_speed")

        # The home location coordinates of the robot. The robot should be 
        # placed at the intersection corresponding to these coordinates to 
        # begin with.
        self._home_location = tuple(settings.get("home_location"))
        self._location = self._home_location
        # The starting direction of the robot. The robot should be aligned with 
        # this direction to begin with.
        self._direction = settings.get("home_direction")

        if self._line_follower_class is None:
            raise NotImplementedError("Subclasses must provide a `_line_follower_class` property")

        self._line_follower = self._line_follower_class(self._home_location, self._direction, self.line_follower_callback, arguments)
        # The delay of the sensor reading loop in the line follower thread.
        self._line_follower_delay = settings.get("line_follower_delay")

        # The delay of the robot vehicle state loop.
        self._loop_delay = settings.get("vehicle_delay")

        self._waypoints = []
        self._current_waypoint = 0

        # Whether the robot is currently armed and driving around.
        self._running = False
        # Current state of the robot. Possible states are:
        # - intersection: The robot is standing still at an intersection.
        # - rotate: The robot is rotating at an intersection. See
        #   Robot_State_Rotate
        self._state = Robot_State("intersection")

    def _state_loop(self):
        while self._running:
            if isinstance(self._state, Robot_State_Rotate):
                if self._state.current_direction == self._state.target_direction:
                    # When we are done rotating, stand still again before 
                    # determining our next moves.
                    self._state = Robot_State("intersection")
                    self.set_speeds(0, 0)

                    self._direction = self._state.current_direction
                    self._line_follower.set_direction(self._direction)
            elif self._state.name == "move":
                if self._last_diverged_time is not None:
                    diff = time.time() - self._last_diverged_time
                    if diff >= self._diverged_time:
                        self.set_speeds(self.speed, self.speed)
                        self._last_diverged_time = None
            elif self._state.name == "intersection":
                if self._location == self.get_waypoint():
                    # We reached the current waypoint.
                    if self._mode.name == "AUTO":
                        # In AUTO mode, immediately try to move to the next 
                        # waypoint, or rotate in the right direction.
                        self._move_waypoint()
                        if self._state.name == "move":
                            self._current_waypoint += 1
                else:
                    # We reached an intersection. Check whether we need to 
                    # rotate here, and otherwise move away from it again.
                    self._move_waypoint()

            time.sleep(self._loop_delay)

    def _line_follower_loop(self):
        while self._running:
            self._line_follower.activate()
            sensor_values = self._line_follower.read()
            self._line_follower.update(sensor_values)
            self._line_follower.deactive()
            time.sleep(self._line_follower_delay)

    def line_follower_callback(self, event, data):
        if event == "intersection":
            self._location = (data[0], data[1])
            self._state = State(event)
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
                    self._state.current_direction = direction
            else:
                # We went off the line, so steer the motors such that the robot 
                # gets back to the line.
                speed = self.speed
                speed_difference = direction * self._diverged_speed
                self.set_speeds(speed - speed_difference, speed + speed_difference)
                self._last_diverged_time = time.time()

    def set_speeds(left_speed, right_speed, left_forward=True, right_forward=True):
        raise NotImplementedError("Subclasses must implement `set_speeds` method")

    @property
    def use_simulation(self):
        # We do not support simulation (physical environments only)
        return False

    @property
    def home_location(self):
        return LocationGlobal(0.0, 0.0, 0.0)

    @home_location.setter
    def home_location(self, value):
        if isinstance(value, LocationLocal):
            self._home_location = (value.north, value.east)
        else:
            print("Warning: Using non-local locations")
            self._home_location = (value.lat, value.lon)

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        if value.name == "RTL":
            self._waypoints = [self._home_location]
        elif value.name == "HALT":
            self._running = False

    @property
    def armed(self):
        return self._running

    @armed.setter
    def armed(self, value):
        if value:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        self._running = True
        thread.start_new_thread(self._line_follower_loop, ())
        thread.start_new_thread(self._state_loop, ())

    def deactivate(self):
        self._running = False

    def add_waypoint(self, location):
        if isinstance(location, LocationLocal):
            self._waypoints.append((location.north, location.east))
        else:
            print("Warning: Using non-local locations")
            self._waypoints.append((location.lat, location.lon))

    def clear_waypoints(self):
        self._waypoints = []

    def get_waypoint(self, waypoint=-1):
        if waypoint == -1:
            waypoint = self._current_waypoint

        if waypoint >= len(self._waypoints):
            return None

        wp = self._waypoints[waypoint]
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
        self.add_waypoint(location)

    @property
    def location(self):
        return LocationLocal(self._location[0], self._location[1], 0.0)

    def _get_yaw(self):
        # TODO: Perhaps we want a more precise attitude... gyroscope?
        if isinstance(self._state, Robot_State_Rotate):
            direction = self._state.current_direction
        else:
            direction = self._direction

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

        return Attitude(0.0, 0.0, yaw)

    def set_yaw(self, heading, relative=False, direction=1):
        if self._state.name != "intersection":
            # We can only rotate on an intersection where we can see all 
            # cardinal lines.
            print("Warning: Cannot change yaw while not on intersection")
            return

        if relative:
            heading = self._get_yaw() + heading

        target_direction = int(round(2*heading/math.pi)) % 4
        self._set_direction(target_direction, direction)

    def _set_direction(self, target_direction, rotate_direction=0):
        if rotate_direction == 0:
            rotate_direction = int(math.copysign(1, target_direction-self._direction))

        self._state = Robot_State_Rotate(rotate_direction, target_direction, self._direction)
        # Keep line follower in intersection state.
        self._line_follower.set_state(Line_Follower_State.AT_INTERSECTION)

        # Start turning the vehicle at turning speed. If we want to rotate 
        # clockwise, the left motor goes forward and the right motor backward, 
        # while counterclockwise is the other way around.
        self.set_speed(self._turning_speed, self._turning_speed, rotate_direction == 1, rotate_direction == -1)

    def _move_waypoint(self):
        if self._current_waypoint + 1 >= len(self._waypoints):
            return

        next_waypoint = self._waypoints[self._current_waypoint+1]
        next_direction = self._next_direction(next_waypoint)
        if next_direction == self._direction:
            # Start moving in the given direction
            self._state = State("move")
            self.set_speeds(self.speed, self.speed)
        else:
            self._set_direction(next_direction)

    def _next_direction(self, waypoint):
        up = waypoint[0] - self._location[0]
        right = waypoint[1] - self._location[1]
        if (
            (self._direction == Line_Follower_Direction.UP and up > 0) or
            (self._direction == Line_Follower_Direction.RIGHT and right > 0) or
            (self._direction == Line_Follower_Direction.DOWN and up < 0) or
            (self._direction == Line_Follower_Direction.LEFT and right < 0)
        ):
            return self._direction

        if right == 0 or self._direction == Line_Follower_Direction.RIGHT or self._direction == Line_Follower_Direction.LEFT:
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
