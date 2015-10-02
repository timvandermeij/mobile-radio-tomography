import sys
import time
import math
from droneapi.lib import VehicleMode, Location, Command
from pymavlink import mavutil
from ..geometry.Geometry import Geometry_Spherical
from MockVehicle import MockVehicle

# Mission trajactory functions
class Mission(object):
    def __init__(self, api, environment, settings):
        self.api = api
        self.environment = environment
        self.vehicle = self.environment.get_vehicle()
        self.is_mock = False
        if isinstance(self.vehicle, MockVehicle):
            self.is_mock = True

        self.geometry = self.environment.get_geometry()
        self.settings = settings
        self._setup()

    def distance_to_current_waypoint(self):
        """
        Gets distance in meters to the current waypoint. 
        It returns `None` for the first waypoint (Home location).
        """
        next_waypoint = self.vehicle.commands.next
        if next_waypoint <= 1:
            return None
        mission_item = self.vehicle.commands[next_waypoint]
        lat = mission_item.x
        lon = mission_item.y
        alt = mission_item.z
        waypoint_location = Location(lat, lon, alt, is_relative=True)
        distance = self.environment.get_distance(waypoint_location)
        return distance

    def _setup(self):
        print("Clear the current mission")
        self.clear_mission()

        print("Create a new mission")
        self.size = self.settings.get("size")
        self.altitude = self.settings.get("altitude")
        self.speed = self.settings.get("speed")
        self.add_square_mission(self.vehicle.location)

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

    def add_square_mission(self, center):
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

        # Define the four MAV_CMD_NAV_WAYPOINT locations and add the commands
        point1 = self.geometry.get_location_meters(center, self.size, -self.size)
        point2 = self.geometry.get_location_meters(center, self.size, self.size)
        point3 = self.geometry.get_location_meters(center, -self.size, self.size)
        point4 = self.geometry.get_location_meters(center, -self.size, -self.size)
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point1.lat, point1.lon, self.altitude))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point2.lat, point2.lon, self.altitude))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point3.lat, point3.lon, self.altitude))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point4.lat, point4.lon, self.altitude))
        cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, point1.lat, point1.lon, self.altitude))

        # Send commands to vehicle.
        self.vehicle.flush()

    def get_commands(self):
        return self.vehicle.commands

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
            # TODO: Check sensors here already?
            print(" Altitude: {} m".format(self.vehicle.location.alt))
            # Just below target, in case of undershoot.
            if self.vehicle.location.alt >= self.altitude * altitude_undershoot:
                print("Reached target altitude")
                break
            time.sleep(1)

    def get_space_size(self):
        return self.size * 4

    def set_speed(self, speed):
        """
        Set the current speed of the vehicle during AUTO mode.
        """
        if self.is_mock:
            # TODO: AUTO mode is not yet supported by mock
            #self.vehicle.velocity =
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

    def set_yaw(self, heading, relative=False):
        """
        Set the bearing `heading` of the vehicle in degrees. This becomes the yaw of the vehicle (the direction in which it is facing).

        This command works in GUIDED mode and only works after a velocity command has been issued.
        If `relative` is false, `heading` is the number of degrees off from northward direction, clockwise.
        If `relative` is true, the `heading` is still given as a bearing, but respective to the vehicle's current yaw.
        """

        if self.is_mock:
            heading = heading * math.pi/180
            if relative:
                self.vehicle.attitude.yaw = self.vehicle.attitude.yaw + heading
            else:
                self.vehicle.attitude.yaw = heading
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
            1,           # param 3, direction -1 ccw, 1 cw
            is_relative, # param 4, relative offset 1, absolute angle 0
            0, 0, 0      # param 5 ~ 7 not used
        )

        # Send command to vehicle
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()
