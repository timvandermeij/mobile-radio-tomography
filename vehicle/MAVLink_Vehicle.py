from dronekit import LocationLocal, Command
from pymavlink import mavutil
from Vehicle import Vehicle

class MAVLink_Vehicle(Vehicle):
    """
    A vehicle that supports some parts of the MAVLink protocol, e.g.,
    mission command sequences or other command message parsing.

    This class assumes the following properties and methods exist:
    - `commands`: A `CommandSequence`-like object, as described in
      http://python.dronekit.io/automodule.html#dronekit.CommandSequence
    - `flush`: A method that might perform backend changes for update_mission,
      but can also be a no-op if no backend changes are necessary in this case.

    Also, all abstract methods from `Vehicle` must also be implemented.
    """

    @property
    def commands(self):
        raise NotImplementedError("Subclasses must provide `commands` property")

    def flush(self):
        raise NotImplementedError("Subclasses must provide `flush` method")

    def clear_waypoints(self):
        self.commands.clear()
        self.flush()

        # After clearing the mission, we must re-download the mission from the 
        # vehicle before vehicle.commands can be used again.
        # See https://github.com/dronekit/dronekit-python/issues/230 for 
        # reasoning.
        self.commands.download()

    def update_mission(self):
        self.commands.upload()
        self.commands.wait_ready()

    def add_takeoff(self, altitude):
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0,
                      0, 0, altitude)
        self.commands.add(cmd)

        return True

    def add_waypoint(self, location):
        # Handle non-spherical geometries
        if isinstance(location, LocationLocal):
            lat, lon, alt = location.north, location.east, -location.down
        else:
            lat, lon, alt = location.lat, location.lon, location.alt

        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                      lat, lon, alt)
        self.commands.add(cmd)

    def add_wait(self):
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM, 0, 0, 0, 0, 0,
                      0, 0, 0, 0)
        self.commands.add(cmd)

    def is_wait(self):
        mission_item = self.commands[self.commands.next]
        return mission_item.command == mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM

    def get_waypoint(self, waypoint=-1):
        """
        Retrieve the Location object corresponding to a waypoint command with ID `waypoint`.
        """

        if waypoint == -1:
            waypoint = self.commands.next

        mission_item = self.commands[waypoint]
        if mission_item.command != mavutil.mavlink.MAV_CMD_NAV_WAYPOINT:
            return None

        lat = mission_item.x
        lon = mission_item.y
        alt = mission_item.z
        return self._geometry.make_location(lat, lon, alt)

    def get_next_waypoint(self):
        return self.commands.next

    def set_next_waypoint(self, waypoint=-1):
        if waypoint == -1:
            waypoint = self.commands.next + 1

        self.commands.next = waypoint

    def count_waypoints(self):
        return self.commands.count

    def is_current_location_valid(self):
        location = self._geometry.get_location_frame(self.location)
        return self.is_location_valid(location)
