import itertools
import sys
import time
import math

import numpy as np

from dronekit import VehicleMode, LocationGlobal, LocationGlobalRelative, LocationLocal

from Memory_Map import Memory_Map
from ..geometry.Geometry import Geometry_Spherical
from ..vehicle.Robot_Vehicle import Robot_Vehicle
from ..zigbee.XBee_Packet import XBee_Packet

# We only list usable missions here, not base classes.
__all__ = [
    "Mission_Browse", "Mission_Cycle", "Mission_Forward",
    "Mission_Infrared", "Mission_Infrared_Grid", "Mission_Pathfind",
    "Mission_Search", "Mission_Square", "Mission_XBee"
]

class Mission(object):
    """
    Mission trajactory utilities.
    This includes generic methods to set up a mission and methods to check and handle actions during the mission.
    Actual missions should be implemented as a subclass.
    """

    def __init__(self, environment, settings):
        self.environment = environment
        self.vehicle = self.environment.get_vehicle()

        self.geometry = self.environment.get_geometry()
        self.settings = settings
        self.memory_map = None

    def distance_to_current_waypoint(self):
        """
        Gets distance in meters to the current waypoint. 
        It returns `None` for the first waypoint (Home location).
        """
        waypoint_location = self.vehicle.get_waypoint()
        if waypoint_location is None:
            return None

        distance = self.environment.get_distance(waypoint_location)
        return distance

    def setup(self):
        # Clear the current mission
        self.clear_mission()

        # Size in meters of one dimension of the part of the space that we are 
        # allowed to be in.
        self.size = self.settings.get("space_size")
        # The number of entries in the memory map per meter
        self.resolution = self.settings.get("resolution")

        # The space around the vehicle's center (where the distance sensor is) 
        # that we do not want to have other objects in. This is used for 
        # additional padding in certain calculations.
        self.padding = self.settings.get("padding")

        # Operating altitude in meters
        self.altitude = self.settings.get("altitude")

        # Speed of the vehicle in meters per second when moving to a location 
        # given in a (goto) command.
        self.speed = self.settings.get("speed")

        # Margin in meters at which we are too close to an object
        self.closeness = self.settings.get("closeness")
        # Distance in meters above which we are uninterested in objects
        self.farness = self.settings.get("farness")

        # Whether to synchronize vehicles at waypoints
        self._xbee_synchronization = self.settings.get("xbee_synchronization")

        # Create a memory map for the vehicle to track where it has seen 
        # objects. This can later be used to find the target object or to fly 
        # around obstacles without colliding.
        # The size is the number of entries in each dimension. We add some 
        # padding to allow for deviations.
        memory_size = (self.size + self.padding)*2
        self.memory_map = Memory_Map(self.environment, memory_size, self.resolution, self.altitude)

    def display(self):
        """
        Display any details about the mission.
        """
        pass

    def clear_mission(self):
        """
        Clear the current mission.
        """

        print('Clearing mission and redownloading default mission...')
        self.vehicle.clear_waypoints()
        self.vehicle.update_mission()

    def check_mission(self):
        print("{} commands in the mission!".format(self.vehicle.count_waypoints()))

        home_location = self.vehicle.home_location
        if home_location is not None:
            print("Home location: {}".format(home_location))
            if isinstance(home_location, LocationGlobal) and isinstance(self.geometry, Geometry_Spherical):
                self.geometry.set_home_location(home_location)

    def get_waypoints(self):
        """
        Retrieve a list of waypoints in this mission.
        The waypoints are `Location` objects.

        The list may be cached, and may be different from waypoints that are
        currently stored in the vehicle.
        """

        return []

    def get_home_location(self):
        return self.vehicle.home_location

    def arm_and_takeoff(self):
        """
        Arms vehicle and fly to the target `altitude`.
        """
        print("Basic pre-arm checks")
        if not self.vehicle.check_arming():
            raise RuntimeError("Could not prepare for arming!")

        print("Arming motors")
        self.vehicle.armed = True

        while not self.vehicle.armed:
            print(" Waiting for arming...")
            time.sleep(1)

        # Take off to target altitude
        print("Taking off!")
        taking_off = self.vehicle.simple_takeoff(self.altitude)
        self.vehicle.speed = self.speed

        if not taking_off:
            return

        # Wait until the vehicle reaches a safe height before processing the 
        # goto (otherwise the command after Vehicle.commands.takeoff will 
        # execute immediately).
        # Allow it to fly to just below target, in case of undershoot.
        altitude_undershoot = self.settings.get("altitude_undershoot")
        alt = self.altitude * altitude_undershoot
        while self.vehicle.location.global_relative_frame.alt < alt:
            print("Altitude: {} m".format(self.vehicle.location.global_relative_frame.alt))
            time.sleep(1)

        print("Reached target altitude")

    def start(self):
        """
        Actually start the mission after arming and flying off.
        """
        raise NotImplementedError("Must be implemented in child class")

    def stop(self):
        """
        Stop the vehicle and the mission immediately.
        """
        self.vehicle.armed = False

    def step(self):
        """
        Perform any calculations for the current vehicle state.
        """
        pass

    def check_sensor_distance(self, sensor_distance, yaw, pitch):
        """
        Decide on doing something with the measured distance.
        If we're too close, we should take action by stopping and going somewhere else.
        Returns `True` if the sensor distance is close enough to be relevant for us.
        """
        if sensor_distance == 0:
            print("Inside the object, abort mission.")
            sys.exit(1)
        elif sensor_distance <= self.closeness:
            self.vehicle.mode = VehicleMode("GUIDED")
            self.vehicle.speed = 0.0
            raise RuntimeError("Too close to the object ({} m), halting.".format(sensor_distance))
        elif sensor_distance < self.farness:
            return True

        return False

    def check_waypoint(self):
        """
        Handle waypoint locations in the mission.
        Only used when this is an AUTO mission.
        We can perform other tasks when we are close to the next waypoint.
        Returns `False` when there are no more commands in the mission.
        """
        return True

    def get_space_size(self):
        return self.size

    def get_memory_map(self):
        return self.memory_map

    def send_global_velocity(self, velocity_x, velocity_y, velocity_z):
        """
        Move vehicle in direction based on specified velocity vectors.

        This should be used in GUIDED mode. See `vehicle.speed` that works in AUTO mode.
        """

        self.vehicle.velocity = [velocity_x, velocity_y, velocity_z]

    def _get_new_yaw(self, heading, relative):
        if relative:
            new_yaw = self.vehicle.attitude.yaw + heading * math.pi/180
        else:
            new_yaw = heading * math.pi/180

        return new_yaw

    def set_yaw(self, heading, relative=False, direction=0):
        """
        Set the bearing `heading` of the vehicle in degrees. This becomes the yaw of the vehicle (the direction in which it is facing). The `heading` is a bearing, meaning that north is zero degrees and increasing counterclockwise.

        This command works in GUIDED mode and only works after a velocity command has been issued.
        If `relative` is false, `heading` is the number of degrees off from northward direction, clockwise.
        If `relative` is true, the `heading` is still given as a bearing, but respective to the vehicle's current yaw.
        The `direction` gives the direction in which we should rotate: 1 is clockwise and -1 is counter. If `direction is 0, then use the direction in which we reach the requested heading the quickest.
        """

        if direction == 0:
            yaw = self.vehicle.attitude.yaw
            new_yaw = self._get_new_yaw(heading, relative)

            # -1 because the yaw is given as a bearing that increases clockwise 
            # while geometry works with angles that increase counterclockwise.
            direction = -1 * self.geometry.get_direction(yaw, new_yaw)

        self.vehicle.set_yaw(heading, relative, direction)

    def set_sensor_yaw(self, heading, relative=False, direction=0):
        """
        Set the yaw for the distance sensors.
        This may be the yaw of the entire vehicle, or changing a servo output.
        In either case, at least one of the distance sensors (if there are any) will in time point in the given direction.
        """
        if not self.environment.get_servos():
            self.set_yaw(heading, relative, direction)
            return

        new_yaw = self._get_new_yaw(heading, relative)
        yaw_angle = self.geometry.bearing_to_angle(new_yaw - self.vehicle.attitude.yaw) * 180/math.pi
        servo = None
        pwm = None
        for servo in self.environment.get_servos():
            if servo.check_value(yaw_angle):
                pwm = servo.get_pwm(yaw_angle)
                self.vehicle.set_servo(servo, pwm)
                return

        self.set_yaw(heading, relative, direction)

    def return_to_launch(self):
        print("Return to launch")
        self.vehicle.mode = VehicleMode("RTL")

class Mission_Auto(Mission):
    """
    A mission that uses the AUTO mode to move to fixed locations.
    """

    def setup(self):
        super(Mission_Auto, self).setup()
        self._waypoints = None
        # Number of waypoints to skip in the commands list; the index of the 
        # first waypoint of our mission. For non-Rover vehicles, we add 
        # a takeoff command to the list that we need not display.
        self._first_waypoint = 1
        self._required_waypoint_sensors = []

    def arm_and_takeoff(self):
        self.add_commands()
        super(Mission_Auto, self).arm_and_takeoff()

    def get_waypoints(self):
        if self._waypoints is None:
            self._waypoints = self.get_points()

        return self._waypoints

    def get_points(self):
        raise NotImplementedError("Must be implemented in child class")

    def add_takeoff(self):
        """
        Add takeoff command. The command is ignored if the vehicle is already
        in the air, or if the vehicle is a ground vehicle. In this case, the
        command may even be not added at all, and the altitude is set to zero.
        """

        has_takeoff = self.vehicle.add_takeoff(self.altitude)
        if not has_takeoff:
            self.altitude = 0.0
            self._first_waypoint = 0

    def add_waypoint(self, point, required_sensors=None):
        """
        Add a waypoint location object `point` to the vehicle's mission command
        waypoints.

        If XBee synchronization is enabled, also adds a wait command afterward.
        The option `required_sensors` list determines which sensors ID to wait
        for in the measurement validation.
        """

        # Handle local locations, points without a specific altitude and 
        # non-spherical geometries.
        if isinstance(point, LocationLocal):
            down = point.down if point.down != 0.0 else -self.altitude
            point = LocationLocal(point.north, point.east, down)
        else:
            alt = point.alt if point.alt != 0.0 else self.altitude
            if isinstance(self.geometry, Geometry_Spherical):
                point = LocationGlobalRelative(point.lat, point.lon, alt)
            else:
                point = LocationLocal(point.lat, point.lon, -alt)

        self.vehicle.add_waypoint(point)

        if self._xbee_synchronization:
            self.vehicle.add_wait()
            self._required_waypoint_sensors.append(required_sensors)

    def add_commands(self):
        """
        Adds a takeoff command and the waypoints to the current mission. 

        The function assumes that the vehicle waypoints are cleared and that we
        can now add the mission waypoints to the vehicle.
        """

        self.add_takeoff()

        # Add the waypoint commands.
        points = self.get_waypoints()
        for point in points:
            self.add_waypoint(point)

        # Send commands to vehicle and update.
        self.vehicle.update_mission()
        self.check_mission()

    def display(self):
        # Make sure that mission being sent is displayed on console cleanly
        time.sleep(self.settings.get("mission_delay"))
        self.check_mission()

    def start(self):
        # Set mode to AUTO to start mission
        self.vehicle.mode = VehicleMode("AUTO")

    def check_waypoint(self):
        if self.vehicle.is_wait():
            if self._xbee_synchronization and self.environment.is_measurement_valid():
                time.sleep(self.settings.get("measurement_delay"))
                print("Measurements are valid, continuing to next waypoint")
                self.vehicle.set_next_waypoint()
                index = self.vehicle.get_next_waypoint() / 2
                if index < len(self._required_waypoint_sensors):
                    required_sensors = self._required_waypoint_sensors[index]
                else:
                    required_sensors = None

                self.environment.invalidate_measurement(required_sensors)
            else:
                return True

        next_waypoint = self.vehicle.get_next_waypoint()
        distance = self.distance_to_current_waypoint()
        if distance is None:
            print('No distance to waypoint known!')
            return True

        if next_waypoint >= self._first_waypoint:
            if distance < self.farness:
                print("Distance to waypoint ({}): {} m".format(next_waypoint, distance))
                if distance <= self.closeness:
                    print("Close enough: skip to next waypoint")
                    self.vehicle.set_next_waypoint()
                    next_waypoint += 1

        return next_waypoint < self.vehicle.count_waypoints()

class Mission_Guided(Mission):
    """
    A mission that uses the GUIDED mode to move on the fly.
    This allows the mission to react to unknown situations determined using sensors.
    """

    def start(self):
        # Set mode to GUIDED. In fact the arming should already have done this, 
        # but it is good to do it here as well.
        self.vehicle.mode = VehicleMode("GUIDED")

# Actual mission implementations

class Mission_Square(Mission_Auto):
    def get_points(self):
        """
        Define the four waypoint locations of a square mission.

        The waypoints are positioned to form a square of side length `2*size` around the specified `center` Location.

        This method returns the points relative to the current location at the same altitude.
        """
        points = []
        points.append(self.environment.get_location(self.size/2, -self.size/2))
        points.append(self.environment.get_location(self.size/2, self.size/2))
        points.append(self.environment.get_location(-self.size/2, self.size/2))
        points.append(self.environment.get_location(-self.size/2, -self.size/2))
        points.append(points[0])
        return points

    def check_waypoint(self):
        if not super(Mission_Square, self).check_waypoint():
            return False

        next_waypoint = self.vehicle.get_next_waypoint()
        num_commands = self.vehicle.count_waypoints()
        if next_waypoint >= num_commands - 1:
            print("Exit 'standard' mission when heading for final waypoint ({})".format(num_commands))
            return False

        return True

class Mission_Forward(Mission_Auto):
    def get_points(self):
        points = []
        points.append(self.environment.get_location(1.0, 0))
        return points

class Mission_Browse(Mission_Guided):
    """
    Mission that stays at a fixed location and scans its surroundings.
    """

    def setup(self):
        super(Mission_Browse, self).setup()
        self.yaw = 0
        self.yaw_angle_step = self.settings.get("yaw_step")

    def step(self):
        # We stand still and change the angle to look around.
        self.send_global_velocity(0,0,0)
        self.set_sensor_yaw(self.yaw, relative=False, direction=1)

        # When we're standing still, we rotate the vehicle to measure distances 
        # to objects.
        self.yaw = (self.yaw + self.yaw_angle_step) % 360

class Mission_Search(Mission_Browse):
    def setup(self):
        super(Mission_Search, self).setup()
        self.move_distance = 0
        self.start_location = self.environment.get_location()

        self.dists_size = 360 / self.yaw_angle_step
        self.dists = np.zeros(self.dists_size)
        self.dists_done = np.zeros(self.dists_size, dtype=bool)

        self.yaw_margin = 5.0 * math.pi/180

    def step(self):
        if self.move_distance > 0:
            moved = self.environment.get_distance(self.start_location)
            d = self.move_distance - moved
            if d <= 0:
                self.move_distance = 0

        if self.move_distance == 0:
            super(Mission_Search, self).step()
            if all(self.dists_done):
                current_location = self.environment.get_location()

                # Find safest "furthest" location (in one line) and move there
                a = self.yaw
                dist = 0
                i = 0
                d_left = 0
                right = 0
                cycle_safe = 0
                safeness = np.zeros(self.dists_size)
                bounds = np.zeros(self.dists_size)
                for d in self.dists:
                    if d == 0:
                        right = right + 1
                    else:
                        dist = d + self.padding + self.closeness
                        angle = (i + right - 1) * self.yaw_angle_step * math.pi/180
                        loc = self.geometry.get_location_angle(current_location, dist, angle)

                        if i == 0:
                            cycle_safe = right
                        elif i == self.dists_size - 1:
                            break
                        else:
                            safeness[i] = right + d_left

                        if self.memory_map.location_in_bounds(loc):
                            d_left = d/float(self.farness)
                        else:
                            d_left = -right

                        safeness[(i + right - 1) % self.dists_size] = right + d_left

                        i = i + right + 1
                        right = 0

                safeness[i % self.dists_size] = right + cycle_safe + d_left

                a = np.argmax(self.dists + safeness)
                dist = self.dists[a]
                if safeness[(a+1) % self.dists_size] > safeness[(a-1) % self.dists_size]:
                    a = a+2
                else:
                    a = a-2

                angle = a * self.yaw_angle_step * math.pi/180
                self.yaw = self.geometry.angle_to_bearing(angle)

                self.move_distance = dist + self.padding + self.closeness
                self.start_location = current_location

                self.dists = np.zeros(self.dists_size)
                self.dists_done = np.zeros(self.dists_size, dtype=bool)

                self.set_yaw(self.yaw * 180/math.pi, relative=False)
                self.vehicle.speed = self.speed
                self.vehicle.simple_goto(self.geometry.get_location_angle(current_location, self.move_distance, angle))

    def check_sensor_distance(self, sensor_distance, yaw, pitch):
        close = super(Mission_Search, self).check_sensor_distance(sensor_distance, yaw, pitch)

        angle_deg = yaw * 180/math.pi
        a = int(angle_deg / self.yaw_angle_step)
        self.dists_done[a] = True
        if sensor_distance < self.farness:
            self.dists[a] = sensor_distance

        if sensor_distance < self.padding + self.closeness:
            if self.geometry.check_angle(self.yaw, self.environment.get_yaw(), self.yaw_margin):
                self.move_distance = 0

        return close

class Mission_Pathfind(Mission_Browse, Mission_Square):
    def add_commands(self):
        pass

    def check_waypoint(self):
        return True

    def start(self):
        super(Mission_Pathfind, self).start()
        self.points = self.get_points()
        self.current_point = -1
        self.next_waypoint = 0
        self.browsing = False
        self.rotating = False
        self.start_yaw = self.yaw
        self.padding = self.settings.get("padding")
        self.sensor_dist = sys.float_info.max

    def get_waypoints(self):
        return self.points

    def distance_to_point(self):
        if self.current_point < 0:
            return 0

        point = self.points[self.current_point]
        return self.environment.get_distance(point)

    def step(self):
        if self.current_point >= len(self.points):
            return

        if self.browsing:
            super(Mission_Pathfind, self).step()
            if self.geometry.check_angle(self.start_yaw, self.yaw, self.yaw_angle_step * math.pi/180):
                self.browsing = False

                points = self.astar(self.vehicle.location.global_relative_frame, self.points[self.next_waypoint])
                if not points:
                    raise RuntimeError("Could not find a suitable path to the next waypoint.")

                self.points[self.current_point:self.next_waypoint] = points
                self.next_waypoint = self.current_point + len(points)
                self.vehicle.speed = self.speed
                self.vehicle.simple_goto(self.points[self.current_point])
                self.rotating = True
                self.start_yaw = self.vehicle.attitude.yaw
        elif self.rotating:
            # Keep track of whether we are rotating because of a goto command.
            if self.geometry.check_angle(self.start_yaw, self.vehicle.attitude.yaw, self.yaw_angle_step * math.pi/180):
                self.rotating = False
                if self.check_scan():
                    return
            else:
                self.start_yaw = self.vehicle.attitude.yaw

        distance = self.distance_to_point()
        print("Distance to current point ({}): {} m".format(self.current_point, distance))
        if self.current_point < 0 or distance <= self.closeness:
            if self.current_point == self.next_waypoint:
                print("Waypoint reached.")
                self.next_waypoint = self.next_waypoint + 1

            self.current_point = self.current_point + 1
            if self.current_point >= len(self.points):
                print("Reached final point.")
                return

            print("Next point ({}): {}".format(self.current_point, self.points[self.current_point]))

            self.vehicle.simple_goto(self.points[self.current_point])

    def check_sensor_distance(self, sensor_distance, yaw, pitch):
        close = super(Mission_Pathfind, self).check_sensor_distance(sensor_distance, yaw, pitch)
        # Do not start scanning if we already are or if we are rotating because 
        # of a goto command.
        self.sensor_dist = sensor_distance
        if not self.browsing and not self.rotating:
            self.check_scan()

        return close

    def check_scan(self):
        if self.sensor_dist < 2 * self.padding + self.closeness:
            print("Start scanning due to closeness.")
            self.send_global_velocity(0,0,0)
            self.browsing = True
            self.start_yaw = self.yaw = self.vehicle.attitude.yaw
            return True

        return False

    def astar(self, start, goal):
        closeness = min(self.sensor_dist - self.padding, self.padding + self.closeness)
        resolution = float(self.memory_map.get_resolution())
        size = self.memory_map.get_size()
        start_idx = self.memory_map.get_index(start)
        goal_idx = self.memory_map.get_index(goal)
        nonzero = self.memory_map.get_nonzero()

        evaluated = set()
        open_nodes = set([start_idx])
        came_from = {}

        # Cost along best known path
        g = np.full((size,size), np.inf)
        g[start_idx] = 0.0

        # Estimated total cost from start to goal when passing through 
        # a specific index.
        f = np.full((size,size), np.inf)
        f[start_idx] = self.cost(start, goal)

        while open_nodes:
            # Get the node in open_nodes with the lowest f score
            open_idx = [idx for idx in open_nodes]
            min_idx = np.argmin(f[[idx[0] for idx in open_idx], [idx[1] for idx in open_idx]])
            current_idx = open_idx[min_idx]
            if current_idx == goal_idx:
                return self.reconstruct(came_from, goal_idx)

            open_nodes.remove(current_idx)
            evaluated.add(current_idx)
            current = self.memory_map.get_location(*current_idx)
            for neighbor_idx in self.neighbors(current_idx):
                if neighbor_idx in evaluated:
                    continue

                try:
                    if self.memory_map.get(neighbor_idx) == 1:
                        continue
                except KeyError:
                    break

                if self.too_close(neighbor_idx, nonzero, closeness, resolution):
                    continue

                neighbor = self.memory_map.get_location(*neighbor_idx)
                tentative_g = g[current_idx] + self.geometry.get_distance_meters(current, neighbor)
                open_nodes.add(neighbor_idx)
                if tentative_g >= g[neighbor_idx]:
                    # Not a better path
                    continue

                came_from[neighbor_idx] = current_idx
                g[neighbor_idx] = tentative_g
                f[neighbor_idx] = tentative_g + self.cost(neighbor, goal)

        return []

    def reconstruct(self, came_from, current):
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
                total_path.append(self.memory_map.get_location(*previous))
            else:
                trend = d

            previous = current

        return list(reversed(total_path))

    def neighbors(self, current):
        y, x = current
        return [(y-1, x-1), (y-1, x), (y-1, x+1),
                (y, x-1),             (y, x+1),
                (y+1, x-1), (y+1, x), (y+1, x+1)]

    def too_close(self, current, nonzero, closeness, resolution):
        for idx in nonzero:
            dist = math.sqrt(((current[0] - idx[0])/resolution)**2 + ((current[1] - idx[1])/resolution)**2)
            if dist < closeness:
                return True

        return False

    def cost(self, start, goal):
        return self.geometry.get_distance_meters(start, goal)

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

class Mission_Infrared_Grid(Mission_Infrared):
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

class Mission_Cycle(Mission_Guided):
    """
    A mission that performs fan beam and straight line measurements on a grid
    using a `Robot_Vehicle`.
    """

    def setup(self):
        super(Mission_Guided, self).setup()

        if not isinstance(self.vehicle, Robot_Vehicle):
            raise ValueError("Mission_Cycle only works with robot vehicles")

        self.done = False
        self.current_waypoint = None

        wpzip = itertools.izip_longest
        grid_size = int(self.size)
        # Last coordinate index of the grid in both directions
        size = grid_size - 1

        location = self.vehicle.location
        if location.north == 0 and location.east == 0:
            self.id = 0
            self.waypoints = itertools.chain(
                # 0
                wpzip(xrange(1, grid_size), [], fillvalue=0),
                # 1
                itertools.chain(
                    wpzip(xrange(size - 1, -1, -1), [], fillvalue=0),
                    wpzip([], xrange(1, grid_size), fillvalue=0)
                ),
                # 2
                wpzip([], xrange(size - 1, -1, -1), fillvalue=0),
                # 3
                itertools.chain(
                    wpzip([], xrange(1, grid_size), fillvalue=0),
                    wpzip(xrange(1, grid_size), [], fillvalue=size)
                ),
                # 4
                wpzip(xrange(size - 1, -1, -1), [], fillvalue=size),
                # 5
                itertools.chain(
                    wpzip(xrange(1, grid_size), [], fillvalue=size),
                    wpzip([], xrange(size - 1, -1, -1), fillvalue=size)
                ),
                # 6
                wpzip([], xrange(1, grid_size), fillvalue=size),
                # 7
                itertools.chain(
                    wpzip([], xrange(size - 1, -1, -1), fillvalue=size),
                    wpzip(xrange(size - 1, -1, -1), [], fillvalue=0)
                )
            )
        elif location.north == 0 and location.east == size:
            self.id = 1
            self.waypoints = itertools.chain(
                # 0
                wpzip(xrange(1, grid_size), [], fillvalue=size),
                # 1
                wpzip(
                    itertools.repeat(size, size * 2),
                    itertools.repeat(size, size * 2)
                ),
                # 2
                wpzip([], xrange(size - 1, -1, -1), fillvalue=size),
                # 3
                wpzip(
                    itertools.repeat(size, size * 2),
                    itertools.repeat(0, size * 2)
                ),
                # 4
                wpzip(xrange(size - 1, -1, -1), [], fillvalue=0),
                # 5
                wpzip(
                    itertools.repeat(0, size * 2),
                    itertools.repeat(0, size * 2)
                ),
                # 6
                wpzip([], xrange(1, grid_size), fillvalue=0),
                # 7
                wpzip(
                    itertools.repeat(0, size * 2),
                    itertools.repeat(size, size * 2)
                )
            )
        else:
            raise ValueError("Vehicle is incorrectly positioned at ({},{}), must be at (0,0) or (0,{})".format(location.north, location.east, size))

    def step(self):
        if self.done:
            return

        if self.current_waypoint is None:
            self.next_waypoint()
        else:
            # Delay to perform measurements. We need to synchronize the robots 
            # so that they both measure at the "valid" location.
            if self.environment.is_measurement_valid():
                self.next_waypoint()
                self.environment.invalidate_measurement()

    def check_waypoint(self):
        return not self.done

    def next_waypoint(self):
        try:
            waypoint = self.waypoints.next()
        except StopIteration:
            self.done = True
            return

        self.current_waypoint = waypoint
        self.vehicle.simple_goto(LocationLocal(waypoint[0], waypoint[1], 0.0))

class Mission_XBee(Mission_Auto):
    def setup(self):
        super(Mission_XBee, self).setup()
        self.environment.add_packet_action("waypoint_clear", self._clear_waypoints)
        self.environment.add_packet_action("waypoint_add", self._add_waypoint)
        self.environment.add_packet_action("waypoint_done", self._complete_waypoints)

        self._waypoints_complete = False
        self._next_index = 0

    def arm_and_takeoff(self):
        # Wait until all the waypoints have been received before arming.
        while not self._waypoints_complete:
            time.sleep(1)

        super(Mission_XBee, self).arm_and_takeoff()

    def _complete_waypoints(self, packet):
        xbee_sensor = self.environment.get_xbee_sensor()
        if xbee_sensor.id != packet.get("to_id"):
            # Ignore packets not meant for us.
            return

        print('Waypoints complete!')

        self._waypoints_complete = True

    def get_points(self):
        return []

    def add_commands(self):
        # Commands are added when they arrive, not in here.
        pass

    def _send_ack(self):
        """
        Send a "waypoint_ack" packet to the ground station.

        This packet mentions which waypoint index we expect next, which is 0
        when we do not have any waypoints anymore or the next unused index
        otherwise.
        """

        xbee_sensor = self.environment.get_xbee_sensor()

        ack_packet = XBee_Packet()
        ack_packet.set("specification", "waypoint_ack")
        ack_packet.set("next_index", self._next_index)
        ack_packet.set("sensor_id", xbee_sensor.id)

        xbee_sensor.enqueue(ack_packet, to=0)

    def _clear_waypoints(self, packet):
        """
        Clear the mission waypoints after receiving a "waypoint_clear" packet.
        """

        xbee_sensor = self.environment.get_xbee_sensor()
        if xbee_sensor.id != packet.get("to_id"):
            # Ignore packets not meant for us.
            return

        self.clear_mission()
        # Add a takeoff command for flying vehicles that use it.
        self.add_takeoff()
        self._next_index = 0
        self._send_ack()

    def _add_waypoint(self, packet):
        """
        Add a waypoint to the mission based on a "waypoint_add" packet.

        The packet must have the XBee sensor ID in the "to_id" field and the
        index must be the next waypoint index; otherwise, the waypoint is not
        added to the vehicle's waypoints.
        """

        xbee_sensor = self.environment.get_xbee_sensor()
        if xbee_sensor.id != packet.get("to_id"):
            # Ignore packets not meant for us.
            return

        index = packet.get("index")
        if index != self._next_index:
            # Send a reply saying what index were are currently at and ignore 
            # the packet, which may be duplicate or out of order.
            self._send_ack()
            return

        latitude = packet.get("latitude")
        longitude = packet.get("longitude")
        altitude = packet.get("altitude")
        wait_id = packet.get("wait_id")

        # Make a location waypoint. `add_waypoint` handles any further 
        # conversion steps.
        point = LocationGlobalRelative(latitude, longitude, altitude)
        required_sensors = [wait_id] if wait_id > 0 else None
        self.add_waypoint(point, required_sensors)
        self._next_index += 1
        self._send_ack()
