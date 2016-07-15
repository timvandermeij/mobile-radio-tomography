import math
import time
from collections import namedtuple
from dronekit import Locations, LocationLocal, LocationGlobal, LocationGlobalRelative

from ..geometry.Geometry_Spherical import Geometry_Spherical
from MAVLink_Vehicle import MAVLink_Vehicle

# Constants used in commands according to mavutil
MAV_FRAME_GLOBAL_RELATIVE_ALT = 3
MAV_CMD_NAV_WAYPOINT = 16
MAV_CMD_NAV_LOITER_UNLIM = 17
MAV_CMD_NAV_TAKEOFF = 22

# Read only classes
VehicleMode = namedtuple('VehicleMode', ['name'])
GPSInfo = namedtuple('GPSInfo', ['eph', 'epv', 'fix_type', 'sattelites_visible'])

GlobalMessage = namedtuple('Message', ['lat', 'lon', 'relative_alt', 'alt'])
LocalMessage = namedtuple('Message', ['x', 'y', 'z'])

class CommandSequence(object):
    def __init__(self, vehicle):
        self._vehicle = vehicle
        self._next = 0
        self._commands = []

    def takeoff(self, altitude):
        if self._vehicle.mode.name == "GUIDED" and self._vehicle.armed:
            self._vehicle.set_target_location(alt=altitude, takeoff=True)

    def goto(self, location):
        self._vehicle.mode = VehicleMode("GUIDED")
        self._vehicle.set_target_location(location=location)

    def add(self, command):
        self._commands.append(command)

    @property
    def count(self):
        return len(self._commands)

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, value):
        self._vehicle.update_location()
        self._next = value
        self._vehicle.clear_target_location()

    def clear(self):
        self._commands = []

    def __getitem__(self, key):
        return self._commands[key]

    def download(self):
        pass

    def upload(self):
        pass

    def wait_ready(self):
        pass

class MockAttitude(object):
    def __init__(self, pitch, yaw, roll, vehicle=None):
        self._pitch = pitch
        self._yaw = yaw
        self._roll = roll
        self.vehicle = vehicle

    def _update(self, pitch=None, yaw=None, roll=None):
        if self.vehicle:
            self.vehicle.update_location()
            if pitch is None and yaw is None and roll is None:
                return

            self.vehicle.set_target_attitude(pitch, yaw, roll)

    @property
    def pitch(self):
        self._update()
        return self._pitch

    @pitch.setter
    def pitch(self, value):
        self._update(pitch=value)

    @property
    def yaw(self):
        self._update()
        return self._yaw

    @yaw.setter
    def yaw(self, value):
        self._update(yaw=value)

    @property
    def roll(self):
        self._update()
        return self._roll

    @roll.setter
    def roll(self, value):
        self._update(roll=value)

    def __eq__(self, other):
        if not isinstance(other, MockAttitude):
            return NotImplemented

        if self._pitch == other._pitch and self._yaw == other._yaw and self._roll == other._roll:
            return True

        return False

class Mock_Vehicle(MAVLink_Vehicle):
    def __init__(self, arguments, geometry, import_manager, thread_manager,
                 usb_manager):
        super(Mock_Vehicle, self).__init__(arguments, geometry, import_manager,
                                           thread_manager, usb_manager)

        # Whether the vehicle has taken off. Affects commands interface.
        self._takeoff = False

        # The current location of the vehicle. Eventually follows the 
        # updated-on-request global relative frame of the vehicle locations.
        self._location = LocationGlobalRelative(0.0, 0.0, 0.0)

        # The target location parsed from commands or a takeoff call.
        self._target_location = None

        # The last time the vehicle location was updated.
        self._update_time = time.time()

        # The current (updated-on-request) attitude of the vehicle.
        self._attitude = MockAttitude(0.0, 0.0, 0.0, self)
        # The target attitude derived from commands or attitude changes
        self._target_attitude = MockAttitude(0.0, 0.0, 0.0, self)
        # The speed in degrees/sec at which pitch/yaw/roll can rotate.
        self._attitude_speed = [10.0, 30.0, 10.0]
        # The direction in which the yaw should change.
        # 1 = clockwise, -1 = counterclockwise.
        self._yaw_direction = 1

        # The requested speed of the vehicle relative to current heading.
        # Overrides the requested velocity if set.
        self._speed = 0.0
        # The requested velocity of the vehicle within (north,east,down) frame.
        self._velocity = [0.0, 0.0, 0.0]

        # The vehicle mode. Can be a "SIMULATED" placeholder, "AUTO", "GUIDED".
        self._mode = VehicleMode("SIMULATED")
        # Mock GPS info (has GPS, but no sattelites)
        self.gps_0 = GPSInfo(0.0, 0.0, 3, 0)

        self._commands = CommandSequence(self)
        self.parameters = {}

        self._home_location = LocationGlobal(0.0, 0.0, 0.0)

        self._location_callback = None
        self._updating = False

        self._message_listeners = {}
        self._locations = Locations(self)
        self.set_location(0.0, 0.0, 0.0)

    @property
    def use_simulation(self):
        return True

    @property
    def commands(self):
        return self._commands

    def _parse_command(self, cmd):
        # Only supported frame
        if cmd is None or cmd.frame != MAV_FRAME_GLOBAL_RELATIVE_ALT:
            self.commands._next = self.commands._next + 1
            return

        if cmd.command == MAV_CMD_NAV_WAYPOINT:
            self.set_target_location(lat=cmd.x, lon=cmd.y, alt=cmd.z)
        elif cmd.command == MAV_CMD_NAV_LOITER_UNLIM:
            # Set target location to False so we can detect this case in 
            # update_location.
            self._target_location = False
        elif cmd.command == MAV_CMD_NAV_TAKEOFF:
            if self._takeoff:
                self.commands._next = self.commands._next + 1
            else:
                self.set_target_location(alt=cmd.z, takeoff=True)

    def set_target_attitude(self, pitch=None, yaw=None, roll=None,
                            yaw_direction=0):
        """
        Set the target attitude of the mock vehicle.

        The mock vehicle will simulate turning to these angles over time.

        The `pitch`, `yaw` and `roll` are in radians for the requested bearings
        (i.e. increasing clockwise from north). The `yaw_direction` can be
        given to rotate the yaw in a specific direction, namely `1` for
        clockwise for and `-1` for counterclockwise. By default, the yaw
        increases in the fastest direction possible.
        """

        if pitch is None:
            pitch = self._attitude._pitch
        if yaw is None:
            yaw = self._attitude._yaw
        if roll is None:
            roll = self._attitude._roll

        self._target_attitude = MockAttitude(pitch, yaw, roll, self)
        if yaw_direction == 0:
            # -1 because the yaw is given as a bearing that increases clockwise 
            # while geometry works with angles that increase counterclockwise.
            current_yaw = self._attitude._yaw
            yaw_direction = -1 * self._geometry.get_direction(current_yaw, yaw)

        self._yaw_direction = yaw_direction

    def set_target_location(self, location=None, lat=None, lon=None, alt=None,
                            takeoff=False):
        """
        Set the target waypoint location of the mock vehicle.

        The mock vehicle will simulate moving to this location over time.

        This can be given as a `location` or as separate `lat`, `lon` and `alt`
        keyword arguments. If any of them are left out, then those coordinate
        components are inherited from the current location. If the target
        location is a takeoff location, then enable `takeoff`.
        """

        if takeoff:
            self._takeoff = True
            self._update_time = time.time()
        elif not self._takeoff:
            return

        if location is not None:
            # Track the target location and convert it so that the remainder of 
            # this method can use global (relative) frame locations.
            self._target_location = location
            target_location = self._make_global_location(location)
        else:
            if lat is None:
                lat = self._location.lat
            if lon is None:
                lon = self._location.lon
            if alt is None:
                alt = self._location.alt

            # Create the target location and track it as an internal location.
            target_location = LocationGlobalRelative(lat, lon, alt)
            self._target_location = self._make_location(LocationGlobalRelative,
                                                        lat, lon, alt)

        # Decide which yaw we need to go to new target location.
        current_coords = (self._location.lat, self._location.lon)
        target_coords = (target_location.lat, target_location.lon)
        if current_coords == target_coords:
            # Moving straight up/down, i.e., no difference in latitude and 
            # longitude, does not require any yaw angle change.
            yaw = self._attitude._yaw
        else:
            a = self._geometry.get_angle(self._locations, self._target_location)
            yaw = self._geometry.angle_to_bearing(a)

        self.set_target_attitude(0.0, yaw, 0.0)

    def clear_target_location(self):
        """
        Remove the target location from the vehicle.
        """

        self._target_location = None

    def _change_attitude(self, field, delta):
        """
        Change an attitude field based on a difference update `delta`.

        Returns `True` if the attitude field is now equal to the target attitude.
        """
        current = getattr(self._attitude, field)
        target = getattr(self._target_attitude, field)
        if self._geometry.check_angle(current, target, abs(delta)):
            setattr(self._attitude, field, target)
            return True
        else:
            setattr(self._attitude, field, (current + delta) % (2*math.pi))
            return False

    def _update_attitude(self, diff):
        """
        Check temporal attitude changes. Update pitch, yaw and roll slowly,
        based on their attitude speeds.

        Returns `True` if a location update is also possible in this timeframe,
        or `False` if we still have more attitude updates to be done.
        """
        if self._target_attitude == self._attitude:
            return True

        dPitch = self._attitude_speed[0] * math.pi/180 * diff
        dYaw = self._attitude_speed[1] * math.pi/180 * diff * self._yaw_direction
        dRoll = self._attitude_speed[2] * math.pi/180 * diff

        pitchDone = self._change_attitude("_pitch", dPitch)
        yawDone = self._change_attitude("_yaw", dYaw)
        rollDone = self._change_attitude("_roll", dRoll)
        if pitchDone and yawDone and rollDone:
            # Allow a speed update already
            return True

        return False

    def _handle_speed(self, dist=0.0, dAlt=0.0):
        a = self._geometry.bearing_to_angle(self._attitude._yaw)
        vNorth = math.sin(a) * self._speed
        vEast = math.cos(a) * self._speed
        if dist != 0.0 and dAlt != 0.0:
            vAlt = dAlt / (dist/self._speed)
        else:
            vAlt = 0.0
        return (vNorth, vEast, vAlt)

    def _update_target_location(self, diff):
        vNorth = 0.0
        vEast = 0.0
        vAlt = 0.0

        if self._speed != 0.0:
            # Move to location with given `speed`. Determine the distance to 
            # the target location, both a normed distance and per-component 
            # difference measures.
            dist = self._geometry.get_distance_meters(self._locations,
                                                      self._target_location)
            dDist = self._geometry.diff_location_meters(self._locations,
                                                        self._target_location)
            dNorth, dEast, dAlt = dDist

            if isinstance(self._geometry, Geometry_Spherical):
                dAlt = self._target_location.alt - self._location.alt
            else:
                dAlt = -self._target_location.down - self._location.alt
                # Handle non-spherical target locations with down component, 
                # when we are close enough to "snap" to the target location.
                # This is the same case as below.
                if (dNorth != 0.0 or dEast != 0.0) and dist < diff * self._speed:
                    self.set_location(dNorth, dEast, dAlt)

            if dNorth != 0.0 or dEast != 0.0:
                # We are moving, but not straight up/down. Check whether the 
                # distance to the target is smaller than the distance that we 
                # can reach in this step, then we "snap" to the exact target 
                # location. Otherwise, we make a step towards it.
                if dist < diff * self._speed:
                    self.location = self._target_location
                else:
                    return self._handle_speed(dist, dAlt)
            elif dAlt != 0.0:
                # We are moving straight up/down. Check whether we can reach 
                # the requested altitude in one step, and update the velocity 
                # to match with such a step. Otherwise, we step towards it.
                if dAlt / diff < self._speed:
                    vAlt = dAlt / diff
                else:
                    vAlt = math.copysign(self._speed, dAlt)
            else:
                # We reached the target location exactly.
                self._target_location = None

        return vNorth, vEast, vAlt

    def _get_delta_time(self):
        new_time = time.time()
        # Seconds since last update (delta time)
        diff = new_time - self._update_time

        return diff, new_time

    def update_location(self):
        """
        Update the current location of the mock vehicle based on time steps.

        Usually this does need to be called externally, because this is
        called when the location or other properties of the vehicle are
        requested, but it may be necessary to call it to propagate changes
        to speed or target locations immediately.
        """

        if not self._takeoff or not self.armed or self._mode.name == "PAUSE":
            return

        diff, new_time = self._get_delta_time()

        # m/s
        vNorth = 0.0
        vEast = 0.0
        vAlt = 0.0

        if not self._update_attitude(diff):
            self._update_time = new_time
            return

        if self._target_location:
            vNorth, vEast, vAlt = self._update_target_location(diff)
        elif self._mode.name == "AUTO" and self._target_location != False:
            if self.commands.count > self.commands.next:
                cmd = self.commands[self.commands.next]
                self._parse_command(cmd)
        elif self._mode.name == "GUIDED":
            vNorth = self._velocity[0]
            vEast = self._velocity[1]
            vAlt = -self._velocity[2]

        north = vNorth * diff
        east = vEast * diff
        alt = vAlt * diff

        self.set_location(north, east, alt)

    @property
    def location(self):
        # If we are not already changing the location in the location setter, 
        # for example when this getter is called from a message listener, then 
        # update the current location before returning it.
        if not self._updating:
            self.update_location()

        return self._locations

    @location.setter
    def location(self, value):
        """
        Update the current location immediately.

        This setter only changes the global and global relative frames of the
        mock vehicle's location.

        This setter should only be used to forcibly change the location of the
        mock vehicle. It is not to be used to alter the target location,
        for which `set_target_location` is responsible.
        """

        if self._updating:
            raise RuntimeError("Recursion detected in location update")

        self._updating = True

        # We need both a "real" LocationGlobal object here for altitude 
        # calculation and the message listener, as well as a location for the 
        # update callback, which should be LocationGlobalRelative in this case.
        value = self._make_global_location(value)
        dalt = (value.alt - self._home_location.alt)

        msg = GlobalMessage(value.lat * 1.0e7, value.lon * 1.0e7, dalt * 1000,
                            value.alt * 1000)
        self.notify_message_listeners('GLOBAL_POSITION_INT', msg)
        self._location = self._locations.global_relative_frame
        self._updating = False
        self._update_time = time.time()

    def set_location(self, north, east, alt):
        """
        Change the location to be at a certain offset from the current location.
        The given arguments `north`, `east` and `alt` are in meters and specify
        the location in those components. The location is immediately updated
        in all frames (global, global relative and local).

        This method should only be used to forcibly change the location of the
        mock vehicle. It is not to be used to alter the target location,
        for which `set_target_location` is responsible.
        """

        local_location = self._locations.local_frame
        if local_location.north is None:
            local_location = LocationLocal(0.0, 0.0, 0.0)

        # First try to set the new location to let the location callback handle 
        # the change.
        new_location = self._geometry.get_location_meters(local_location, north, east, alt)
        self.location = new_location
        self._updating = True

        # Send a message to the message listeners
        msg = LocalMessage(local_location.north + north,
                           local_location.east + east,
                           local_location.down - alt)
        self.notify_message_listeners('LOCAL_POSITION_NED', msg)
        self._updating = False

    def on_message(self, name):
        def decorator(fn):
            if name not in self._message_listeners:
                self._message_listeners[name] = []
            if fn not in self._message_listeners[name]:
                self._message_listeners[name].append(fn)

        return decorator

    def notify_message_listeners(self, name, msg):
        for fn in self._message_listeners.get(name, []):
            fn(self, name, msg)
        for fn in self._message_listeners.get('*', []):
            fn(self, name, msg)

    @property
    def attitude(self):
        self.update_location()
        return self._attitude

    @attitude.setter
    def attitude(self, value):
        if not isinstance(value, MockAttitude):
            raise TypeError("Must be given a MockAttitude.")

        # No need to update since this forces a new attitude
        value.vehicle = self
        self._attitude = value

    def set_yaw(self, heading, relative=False, direction=1):
        heading = heading * math.pi/180
        if relative:
            self.set_target_attitude(yaw=self.attitude.yaw + heading, yaw_direction=direction)
        else:
            self.set_target_attitude(yaw=heading, yaw_direction=direction)

    def set_servo(self, servo, pwm):
        servo.set_current_pwm(pwm)

    @property
    def speed(self):
        self.update_location()
        return self._speed

    @speed.setter
    def speed(self, value):
        self.update_location()
        self._speed = value
        self._velocity = [0.0, 0.0, 0.0]

    @property
    def velocity(self):
        self.update_location()
        return self._velocity

    @velocity.setter
    def velocity(self, value):
        # Update with old velocity before applying new one
        self.update_location()
        self._velocity = value
        self._speed = 0.0

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        # Update with old velocity before applying new mode
        self.update_location()
        self._mode = value
        # Clear target location so new mode can give its own
        self._target_location = None

    def check_arming(self):
        self.mode = VehicleMode("GUIDED")

        return True

    def pause(self):
        self.mode = VehicleMode("PAUSE")

    def simple_takeoff(self, altitude):
        self.commands.takeoff(altitude)

    def simple_goto(self, location):
        self.commands.goto(location)

    @property
    def airspeed(self):
        return 0.0

    @property
    def groundspeed(self):
        return 0.0

    @property
    def home_location(self):
        return self._make_location(LocationGlobal,
                                   self._home_location.lat,
                                   self._home_location.lon,
                                   self._home_location.alt)

    @home_location.setter
    def home_location(self, value):
        self._home_location = self._make_global_location(value)

    def _make_location(self, location_class, lat, lon, alt):
        if isinstance(self._geometry, Geometry_Spherical):
            return location_class(lat, lon, alt)

        return LocationLocal(lat - self._home_location.lat,
                             lon - self._home_location.lon,
                             self._home_location.alt - alt)

    def flush(self):
        pass
