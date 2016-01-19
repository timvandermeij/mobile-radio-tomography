import sys
import time
import math

import numpy as np

from droneapi.lib import VehicleMode, Location, Command
from pymavlink import mavutil

from ..geometry.Geometry import Geometry_Spherical
from Memory_Map import Memory_Map
from MockVehicle import MockVehicle

class Mission(object):
    """
    Mission trajactory utilities.
    This includes generic methods to set up a mission and methods to check and handle actions during the mission.
    Actual missions should be implemented as a subclass.
    """

    def __init__(self, api, environment, settings):
        self.api = api
        self.environment = environment
        self.vehicle = self.environment.get_vehicle()
        self.is_mock = False
        if isinstance(self.vehicle, MockVehicle):
            self.is_mock = True

        self.geometry = self.environment.get_geometry()
        self.settings = settings
        self.memory_map = None

    def distance_to_current_waypoint(self):
        """
        Gets distance in meters to the current waypoint. 
        It returns `None` for the first waypoint (Home location).
        """
        next_waypoint = self.vehicle.commands.next
        if next_waypoint <= 1:
            return None
        waypoint_location = self.get_waypoint(next_waypoint)
        distance = self.environment.get_distance(waypoint_location)
        return distance

    def get_waypoint(self, waypoint, is_relative=True):
        """
        Retrieve the Location object corresponding to a waypoint command with ID `waypoint`.
        """
        mission_item = self.vehicle.commands[waypoint]
        lat = mission_item.x
        lon = mission_item.y
        alt = mission_item.z
        waypoint_location = Location(lat, lon, alt, is_relative=is_relative)
        return waypoint_location

    def setup(self):
        # Clear the current mission
        self.clear_mission()

        # Older versions of dronekit do not have a home_location property, so 
        # we need to retrieve it from the waypoint commands ourselves.
        if hasattr(self.vehicle, "home_location"):
            self.geometry.set_home_location(self.vehicle.home_location)
        else:
            home_location = self.get_waypoint(0, is_relative=False)
            self.geometry.set_home_location(home_location)

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
        cmds = self.vehicle.commands
        self.vehicle.commands.clear()
        self.vehicle.flush()

        # After clearing the mission, we MUST re-download the mission from the 
        # vehicle before vehicle.commands can be used again.
        # See https://github.com/dronekit/dronekit-python/issues/230 for 
        # reasoning.
        self.download_mission()

    def download_mission(self):
        """
        Download the current mission from the vehicle.
        """
        cmds = self.vehicle.commands
        cmds.download()
        # Wait until download is complete.
        cmds.wait_valid()

    def get_commands(self):
        return self.vehicle.commands

    def get_waypoints(self):
        return []

    def get_home_location(self):
        return self.vehicle.home_location

    def arm_and_takeoff(self):
        """
        Arms vehicle and fly to the target `altitude`.
        """
        print("Basic pre-arm checks")
        # Don't let the user try to fly autopilot is booting
        while self.vehicle.mode.name == "INITIALISING":
            print("Waiting for vehicle to initialise...")
            time.sleep(1)
        while self.vehicle.gps_0.fix_type < 2:
            print("Waiting for GPS...: {}".format(self.vehicle.gps_0.fix_type))
            time.sleep(1)

        print("Arming motors")
        # Copter should arm in GUIDED mode
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.armed = True
        self.vehicle.flush()

        while not self.vehicle.armed and not self.api.exit:
            print(" Waiting for arming...")
            time.sleep(1)

        # Take off to target altitude
        print("Taking off!")
        self.vehicle.commands.takeoff(self.altitude)
        self.set_speed(self.speed)
        self.vehicle.flush()

        # Wait until the vehicle reaches a safe height before processing the 
        # goto (otherwise the command after Vehicle.commands.takeoff will 
        # execute immediately).
        altitude_undershoot = self.settings.get("altitude_undershoot")
        while not self.api.exit:
            print(" Altitude: {} m".format(self.vehicle.location.alt))
            # Just below target, in case of undershoot.
            if self.vehicle.location.alt >= self.altitude * altitude_undershoot:
                print("Reached target altitude")
                break
            time.sleep(1)

    def start(self):
        """
        Actually start the mission after arming and flying off.
        """
        raise NotImplementedError("Must be implemented in child class")

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
        elif sensor_distance < self.closeness:
            self.vehicle.mode = VehicleMode("GUIDED")
            self.set_speed(0)
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

    def set_speed(self, speed):
        """
        Set the current speed of the vehicle during AUTO or GUIDED mode.
        """
        if self.is_mock:
            self.vehicle.speed = speed
            return

        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # command
            0, # confirmation
            0, # param 1
            speed, # speed in meters/second
            0, 0, 0, 0, 0 # param 3 - 7
        )

        # Send command to vehicle
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()

    def send_global_velocity(self, velocity_x, velocity_y, velocity_z):
        """
        Move vehicle in direction based on specified velocity vectors.

        This should be used in GUIDED mode. See `set_speed` for another command that works in AUTO mode.
        """
        if self.is_mock:
            self.vehicle.velocity = [velocity_x, velocity_y, velocity_z]
            return

        msg = self.vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, # frame
            0b0000111111000111, # type_mask (only speeds enabled)
            0, # lat_int - X Position in WGS84 frame in 1e7 * meters
            0, # lon_int - Y Position in WGS84 frame in 1e7 * meters
            0, # alt - Altitude in meters in AMSL altitude(not WGS84 if absolute or relative)
                        # altitude above terrain if GLOBAL_TERRAIN_ALT_INT
            velocity_x, # X velocity in NED frame in m/s
            velocity_y, # Y velocity in NED frame in m/s
            velocity_z, # Z velocity in NED frame in m/s
            0, 0, 0,    # afx, afy, afz acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)       # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)
        # send command to vehicle
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()

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
            if relative:
                new_yaw = yaw + heading * math.pi/180
            else:
                new_yaw = heading * math.pi/180

            # -1 because the yaw is given as a bearing that increases clockwise 
            # while geometry works with angles that increase counterclockwise.
            direction = -1 * self.geometry.get_direction(yaw, new_yaw)

        if self.is_mock:
            heading = heading * math.pi/180
            if relative:
                self.vehicle.set_target_attitude(yaw=self.vehicle.attitude.yaw + heading, yaw_direction=direction)
            else:
                self.vehicle.set_target_attitude(yaw=heading, yaw_direction=direction)

            return

        if relative:
            is_relative = 1 # yaw relative to direction of travel
        else:
            is_relative = 0 # yaw is an absolute angle

        # Create the CONDITION_YAW command using command_long_encode()
        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_CONDITION_YAW, # command
            0, # confirmation
            heading,     # param 1, yaw in degrees
            1,           # param 2, yaw speed deg/s (ignored)
            direction,   # param 3, direction -1 ccw, 1 cw
            is_relative, # param 4, relative offset 1, absolute angle 0
            0, 0, 0      # param 5 ~ 7 not used
        )

        # Send command to vehicle
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()

    def return_to_launch(self):
        print("Return to launch")
        self.vehicle.mode = VehicleMode("RTL")
        # Flush to ensure changes are sent to autopilot
        self.vehicle.flush()

class Mission_Auto(Mission):
    """
    A mission that uses the AUTO mode to move to fixed locations.
    """

    def setup(self):
        super(Mission_Auto, self).setup()
        self._waypoints = None
        self.add_commands()

    def get_waypoints(self):
        if self._waypoints is None:
            self._waypoints = self.get_points()

        return self._waypoints

    def get_points(self):
        raise NotImplementedError("Must be implemented in child class")

    def add_commands(self):
        """
        Adds a takeoff command and four waypoint commands to the current mission. 
        The waypoints are positioned to form a square of side length `2*size` around the specified `center` Location.

        The function assumes `vehicle.commands` is the vehicle mission state 
        (you must have called `download_mission` at least once before in the session and after any use of `clear_mission`)
        """
        # Add the commands. The meaning/order of the parameters is documented 
        # in the Command class.
        cmds = self.vehicle.commands
        # Add MAV_CMD_NAV_TAKEOFF command. This is ignored if the vehicle is 
        # already in the air.
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 0, self.altitude))

        # Add the MAV_CMD_NAV_WAYPOINT commands.
        points = self.get_waypoints()
        for point in points:
            cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point.lat, point.lon, self.altitude))

        # Send commands to vehicle.
        self.vehicle.flush()

    def display(self):
        # Make sure that mission being sent is displayed on console cleanly
        time.sleep(self.settings.get("mission_delay"))
        num_commands = self.vehicle.commands.count
        print("{} commands in the mission!".format(num_commands))

    def start(self):
        # Set mode to AUTO to start mission
        self.vehicle.mode = VehicleMode("AUTO")
        self.vehicle.flush()

    def check_waypoint(self):
        next_waypoint = self.vehicle.commands.next
        distance = self.distance_to_current_waypoint()
        if next_waypoint > 1:
            if distance < self.farness:
                print("Distance to waypoint ({}): {} m".format(next_waypoint, distance))
                if distance < self.closeness:
                    print("Close enough: skip to next waypoint")
                    self.vehicle.commands.next = next_waypoint + 1
                    next_waypoint = next_waypoint + 1

        num_commands = self.vehicle.commands.count
        if next_waypoint >= num_commands:
            print("Exit 'standard' mission when heading for final waypoint ({})".format(num_commands))
            return False

        return True

class Mission_Guided(Mission):
    """
    A mission that uses the GUIDED mode to move on the fly.
    This allows the mission to react to unknown situations determined using sensors.
    """

    def start(self):
        # Set mode to GUIDED. In fact the arming should already have done this, 
        # but it is good to do it here as well.
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.flush()

# Actual mission implementations

class Mission_Square(Mission_Auto):
    def get_points(self):
        """
        Define the four waypoint locations.
        This method returns the points relative to the current location at the same altitude.
        """
        points = []
        points.append(self.environment.get_location(self.size/2, -self.size/2))
        points.append(self.environment.get_location(self.size/2, self.size/2))
        points.append(self.environment.get_location(-self.size/2, self.size/2))
        points.append(self.environment.get_location(-self.size/2, -self.size/2))
        points.append(points[0])
        return points

class Mission_Forward(Mission_Auto):
    def get_points(self):
        points = []
        points.append(self.environment.get_location(0.25, 0))
        points.append(self.environment.get_location(0, 0))
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
        self.vehicle.flush()
        self.set_yaw(self.yaw, relative=False, direction=1)
        print("Yaw: {} Expected: {}".format(self.vehicle.attitude.yaw*180/math.pi, self.yaw))

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
                self.set_speed(self.speed)
                self.vehicle.commands.goto(self.geometry.get_location_angle(current_location, self.move_distance, angle))

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

                points = self.astar(self.vehicle.location, self.points[self.next_waypoint])
                if not points:
                    raise RuntimeError("Could not find a suitable path to the next waypoint.")

                self.points[self.current_point:self.next_waypoint] = points
                self.next_waypoint = self.current_point + len(points)
                self.set_speed(self.speed)
                self.vehicle.commands.goto(self.points[self.current_point])
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
        if self.current_point < 0 or distance < self.closeness:
            if self.current_point == self.next_waypoint:
                print("Waypoint reached.")
                self.next_waypoint = self.next_waypoint + 1

            self.current_point = self.current_point + 1
            if self.current_point >= len(self.points):
                print("Reached final point.")
                return

            print("Next point: {i}: Location({p.lat}, {p.lon}, is_relative={p.is_relative})".format(i=self.current_point, p=self.points[self.current_point]))

            self.vehicle.commands.goto(self.points[self.current_point])

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
            self.vehicle.flush()
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
