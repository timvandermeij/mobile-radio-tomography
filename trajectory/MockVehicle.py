from collections import namedtuple

Location = namedtuple('Location',['lat', 'lon', 'alt', 'is_relative'])
VehicleMode = namedtuple('VehicleMode',['name'])
GPSInfo = namedtuple('GPSInfo',['eph','epv','fix_type','sattelites_visible'])

# TODO: Update vehicle location/etc on access to public stuff

class CommandSequence(object):
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.next = 0
        self.commands = []

    def takeoff(self, altitude):
        # Fast!
        self.vehicle._alt = altitude

    def add(self, command):
        self.commands.append(command)

    @property
    def count(self):
        return len(self.commands)

    def clear(self):
        self.commands = []

    def download(self):
        pass

    def wait_valid(self):
        pass

class MockAttitude(object):
    def __init__(self, pitch, yaw, roll):
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll

class MockVehicle(object):
    def __init__(self):
        self._lat = 0.0
        self._lon = 0.0
        self._alt = 0.0
        self.attitude = MockAttitude(0.0,0.0,0.0)
        self.velocity = [0.0,0.0,0.0]
        self.mode = VehicleMode("SIMULATED")
        self.armed = False
        self.gps_0 = GPSInfo(0.0,0.0,3,0)
        self.commands = CommandSequence(self)

    @property
    def location(self):
        return Location(self._lat, self._lon, self._alt, True)

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
