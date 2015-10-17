import math
import time
from collections import namedtuple

# Constants used in commands according to mavutil
MAV_FRAME_GLOBAL_RELATIVE_ALT = 3
MAV_CMD_NAV_WAYPOINT = 16
MAV_CMD_NAV_TAKEOFF = 22

# Read only classes
Location = namedtuple('Location',['lat', 'lon', 'alt', 'is_relative'])
VehicleMode = namedtuple('VehicleMode',['name'])
GPSInfo = namedtuple('GPSInfo',['eph','epv','fix_type','sattelites_visible'])

class CommandSequence(object):
    def __init__(self, vehicle):
        self._vehicle = vehicle
        self._next = 0
        self._commands = [None] # Dummy "home location" command

    def takeoff(self, altitude):
        if self._vehicle.mode.name == "GUIDED" and self._vehicle.armed:
            self._vehicle._set_target_location(alt=altitude, takeoff=True)

    def goto(self, location):
        self._vehicle.mode = VehicleMode("GUIDED")
        self._vehicle._set_target_location(location=location)

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
        self._vehicle._update_location()
        self._next = value
        self._vehicle._target_location = None

    def clear(self):
        self._commands = [None]

    def __getitem__(self, key):
        return self._commands[key]

    def download(self):
        pass

    def wait_valid(self):
        pass

class MockAttitude(object):
    def __init__(self, pitch, yaw, roll):
        self._pitch = pitch
        self._yaw = yaw
        self._roll = roll

    @property
    def pitch(self):
        return self._pitch

    @property
    def yaw(self):
        return self._yaw

    @yaw.setter
    def yaw(self, value):
        self._yaw = value

    @property
    def roll(self):
        return self._roll

class MockVehicle(object):
    def __init__(self, geometry):
        self._geometry = geometry
        self._takeoff = False
        self._location = Location(0.0, 0.0, 0.0, True)
        self._target_location = None
        self._update_time = time.time()
        self.attitude = MockAttitude(0.0,0.0,0.0)
        self._speed = 0.0 # Relative to current heading
        self._velocity = [0.0,0.0,0.0] # NED
        self._mode = VehicleMode("SIMULATED")
        self.armed = False
        self.gps_0 = GPSInfo(0.0,0.0,3,0)
        self.commands = CommandSequence(self)

    def _parse_command(self, cmd):
        # Only supported frame
        if cmd is None or cmd.frame != MAV_FRAME_GLOBAL_RELATIVE_ALT:
            self.commands._next = self.commands._next + 1
            return

        if cmd.command == MAV_CMD_NAV_WAYPOINT:
            self._set_target_location(lat=cmd.x, lon=cmd.y, alt=cmd.z)
        elif cmd.command == MAV_CMD_NAV_TAKEOFF:
            if self._takeoff:
                self.commands._next = self.commands._next + 1
            else:
                self._set_target_location(alt=cmd.z, takeoff=True)

    def _set_target_location(self, location=None, lat=None, lon=None, alt=None, takeoff=False):
        if takeoff:
            self._takeoff = True
            self._update_time = time.time()
        elif not self._takeoff:
            return

        if location is not None:
            self._target_location = location
        else:
            if lat is None:
                lat = self._location.lat
            if lon is None:
                lon = self._location.lon
            if alt is None:
                alt = self._location.alt
            self._target_location = Location(lat, lon, alt, True)

        # Change yaw to go to new target location
        # This is Fast! Which means that it skips location updates (since we're 
        # likely to be in one) and the yaw update is not yet governed by speed 
        # but is instead instantaneous, which is unrealistic.
        # TODO: Add suppoprt for temporal attitude updates (i.e. changing the 
        # yaw slowly in time based on yaw speed)
        a = self._geometry.get_angle(self._location, self._target_location)
        self.attitude._yaw = self._geometry.angle_to_bearing(a)

    def _handle_speed(self, dist=0.0, dAlt=0.0):
        a = self._geometry.bearing_to_angle(self.attitude._yaw)
        print(self.attitude._yaw, a)
        vNorth = math.sin(a) * self._speed
        vEast = math.cos(a) * self._speed
        if dist != 0.0 and dAlt != 0.0:
            vAlt = dAlt / (dist/self._speed)
        else:
            vAlt = 0.0
        return (vNorth, vEast, vAlt)

    def _update_location(self, altitude=None):
        if not self._takeoff:
            return

        new_time = time.time()
        # seconds since last update (delta time)
        diff = new_time - self._update_time
        # m/s
        vNorth = 0.0
        vEast = 0.0
        vAlt = 0.0

        if self._target_location is not None:
            if self._speed != 0.0:
                # Move to location with given `speed`
                dist = self._geometry.get_distance_meters(self._location, self._target_location)
                dAlt = self._target_location.alt - self._location.alt
                if dist != 0.0:
                    vNorth, vEast, vAlt = self._handle_speed(dAlt, dist)
                elif dAlt != 0.0:
                    if dAlt / diff < self._speed:
                        vAlt = dAlt / diff
                    else:
                        vAlt = math.copysign(self._speed, dAlt)
                else:
                    # Reached target location.
                    print("Reached target location")
                    self._target_location = None
                    self.commands.next = self.commands.next + 1
        elif self._mode.name == "AUTO" and self.commands.count > self.commands.next:
            cmd = self.commands[self.commands.next]
            self._parse_command(cmd)
        elif self._mode.name == "GUIDED":
            if self._speed != 0.0:
                vNorth, vEast, vAlt = self._handle_speed()
                print(vNorth, vEast, vAlt)
            else:
                vNorth = self._velocity[0]
                vEast = self._velocity[1]
                vAlt = -self._velocity[2]

        north = vNorth * diff
        east = vEast * diff
        alt = vAlt * diff

        self.set_location(north, east, alt)
        self._update_time = new_time

    @property
    def location(self):
        self._update_location()
        return self._location

    @location.setter
    def location(self, value):
        # No need to update since this forces a new location
        self._location = value

    def set_location(self, north, east, alt):
        l = self._geometry.get_location_meters(self._location, north, east, alt)
        self._location = l

    @property
    def speed(self):
        self._update_location()
        return self._speed

    @speed.setter
    def speed(self, value):
        self._update_location()
        self._speed = value
        self._velocity = [0.0,0.0,0.0]

    @property
    def velocity(self):
        self._update_location()
        return self._velocity

    @velocity.setter
    def velocity(self, value):
        # Update with old velocity before applying new one
        self._update_location()
        self._velocity = value
        self._speed = 0.0

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        # Update with old velocity before applying new mode
        self._update_location()
        self._mode = value
        # Clear target location so new mode can give its own
        self._target_location = None

    @property
    def airspeed(self):
        return 0.0

    @property
    def groundspeed(self):
        return 0.0

    def flush(self):
        pass

class MockAPI(object):
    def __init__(self):
        self.exit = False
