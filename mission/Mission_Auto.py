import time
from dronekit import LocationLocal, VehicleMode
from Mission import Mission

class Mission_Auto(Mission):
    """
    A mission that uses the AUTO mode to move to fixed locations.
    """

    def setup(self):
        super(Mission_Auto, self).setup()

        # Cached waypoints from the `get_points` implemented by the actual 
        # mission. The cached points are obtainable through `get_waypoints`.
        self._waypoints = None

        # Number of waypoints to skip in the commands list; the index of the 
        # first waypoint of our mission. For non-Rover vehicles, we add 
        # a takeoff command to the list that we need not display.
        self._first_waypoint = 1

        # Dictionary containing information related to "wait" waypoints. Each 
        # key is an index of a waypoint just before the vehicle's "wait" 
        # waypoint, and its value is a dictionary with the following contents: 
        # - "sensors": a list of sensor IDs of other vehicles to synchronize
        #   with. We do not continue from this waypoint until all of them are 
        #   synchronized with the current vehicle.
        # - "own_waypoint": the wait waypoint ID of the current vehicle. This
        #   is different from the waypoint index, as the wait waypoint ID only 
        #   counts the "wait" waypoints. This ID is sent to other vehicles to 
        #   inform them for synchronization purposes.
        # - "wait_waypoint": the wait waypoint ID of the vehicles to wait for.
        self._wait_waypoints = {}

    def arm_and_takeoff(self):
        try:
            self.add_commands()
        except RuntimeError:
            pass

        self._set_measurement_validation(0)

        super(Mission_Auto, self).arm_and_takeoff()

    def get_waypoints(self):
        if self._waypoints is None:
            self._waypoints = self.get_points()

        return self._waypoints

    def get_points(self):
        """
        Retrieve a list of waypoint locations for this mission.

        This list is cached by `get_waypoints`.
        """

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

    def _convert_waypoint(self, point):
        """
        Convert a waypoint location object `point` to adhere to the current
        geometry's location and mission's operating altitude.
        """

        # Handle local locations, points without a specific altitude and 
        # non-spherical geometries.
        if isinstance(point, LocationLocal):
            down = point.down if point.down != 0.0 else -self.altitude
            return LocationLocal(point.north, point.east, down)

        alt = point.alt if point.alt != 0.0 else self.altitude
        return self.geometry.make_location(point.lat, point.lon, alt)

    def add_waypoint(self, point, wait=True, required_sensors=None,
                     wait_waypoint=-1):
        """
        Add a waypoint location object `point` to the vehicle's mission command
        waypoints.

        If RF sensor synchronization is enabled and `wait` is `True`, then this
        also adds a wait command afterward. `required_sensors` is a list which
        determines which sensors ID to wait for in the measurement validation.
        If it is not given, then we assume we have to wait for all sensors.
        `wait_waypoint` indicates the index of the waypoint of the other
        vehicle(s) to synchronize with; if it is `-1`, then it is assumed to be
        the index of this vehicle's waypoint.
        """

        # Index of our own waypoint, to store the relevant information for any 
        # "wait" waypoints. Needs to be obtained before we add the actual 
        # waypoint.
        index = self.vehicle.count_waypoints()
        if wait_waypoint == -1:
            wait_waypoint = len(self._wait_waypoints)

        self.vehicle.add_waypoint(self._convert_waypoint(point))

        if self._rf_sensor_synchronization and wait:
            self.vehicle.add_wait()

            self._wait_waypoints[index] = {
                "sensors": required_sensors,
                "own_waypoint": len(self._wait_waypoints),
                "other_waypoint": wait_waypoint
            }

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

    def step(self):
        # AUTO missions usually do not need to perform a step.
        pass

    def _check_measurements(self):
        """
        Check whether measurements have become valid, assuming that the vehicle
        is waiting for this event. If so, schedule the next measurements
        validation moment. Returns `True` if measurements are valid and the
        vehicle is continuing to the next waypoint, and `False` if it is still
        waiting at this waypoint.
        """

        # The wait waypoints dictionary is indexed by the waypoint before the 
        # actual "wait" waypoint (which we are currently at). Let the 
        # measurement validation know that we are at the correct sensor 
        # location, so we can perform the measurement.
        waypoint_index = self.vehicle.get_next_waypoint() - 1
        if waypoint_index in self._wait_waypoints:
            self.environment.set_waypoint_valid()

        if not self.environment.is_measurement_valid():
            return False

        # The vehicle is waiting for measurements to become valid, and they 
        # have, so go to the next waypoint. We do not need to give an explicit 
        # waypoint here, unlike in `check_waypoint`, since the vehicle never 
        # changes the waypoint in between this code.
        print("Measurements are valid, continuing to next waypoint")
        self.vehicle.set_next_waypoint()
        index = self.vehicle.get_next_waypoint()
        self._set_measurement_validation(index)

        return True

    def _set_measurement_validation(self, index):
        if index in self._wait_waypoints:
            sensors = self._wait_waypoints[index]["sensors"]
            own_waypoint = self._wait_waypoints[index]["own_waypoint"]
            wait_waypoint = self._wait_waypoints[index]["other_waypoint"]
            immediately_valid = False
        else:
            print("No more wait waypoints registered for this mission, falling back to default wait waypoints")
            sensors = None
            own_waypoint = index
            wait_waypoint = index
            immediately_valid = True

        self.environment.invalidate_measurement(required_sensors=sensors,
                                                own_waypoint=own_waypoint,
                                                wait_waypoint=wait_waypoint)

        if immediately_valid:
            self.environment.set_waypoint_valid()

    def check_wait(self):
        """
        Handle wait waypoints in the mission.

        Returns `False` if the current waypoint should still be handled by
        `check_waypoint`, i.e., if it is not a wait point or if we have
        finished waiting at that point. In the latter case, the vehicle's
        waypoint is updated and the measurements are invalidated.
        """

        if self.vehicle.is_wait():
            if self._rf_sensor_synchronization:
                return not self._check_measurements()

            return True

        return False

    def check_waypoint(self):
        if self.check_wait():
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
                    # We are close enough to the waypoint, so skip to the next 
                    # one so that we vehicle can prepare itself for that. We 
                    # pass an explicit waypoint number to avoid race conditions 
                    # with the vehicle's AUTO mode changing it in the meantime.
                    print("Close enough: skip to next waypoint")
                    self.vehicle.set_next_waypoint(next_waypoint + 1)
                    next_waypoint += 1

        return next_waypoint < self.vehicle.count_waypoints()
