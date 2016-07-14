import time
from Mission_Auto import Mission_Auto
from ..waypoint.Waypoint import Waypoint, Waypoint_Type
from ..zigbee.Packet import Packet

class Mission_RF_Sensor(Mission_Auto):
    def setup(self):
        super(Mission_RF_Sensor, self).setup()

        self.environment.add_packet_action("waypoint_clear", self._clear_waypoints)
        self.environment.add_packet_action("waypoint_add", self._add_waypoint)
        self.environment.add_packet_action("waypoint_done", self._complete_waypoints)

        self._waypoints_complete = False
        self._next_index = 0
        self._point = None

        self._rf_sensor = self.environment.get_rf_sensor()
        if self._rf_sensor is None:
            raise ValueError("An RF sensor must be enabled for `Mission_RF_Sensor`")

    def arm_and_takeoff(self):
        self.check_mission()

        # Wait until all the waypoints have been received before arming.
        while not self._waypoints_complete:
            time.sleep(1)

        super(Mission_RF_Sensor, self).arm_and_takeoff()

    def _complete_waypoints(self, packet):
        if self._rf_sensor.id != packet.get("to_id"):
            # Ignore packets not meant for us.
            return

        print('Waypoints complete!')

        self._waypoints_complete = True

    @property
    def waypoints_complete(self):
        """
        Accessor for whether all the waypoints have been received.
        """

        return self._waypoints_complete

    @property
    def next_index(self):
        """
        Accessor for the next waypoint index that should be received from the
        ground station.
        """

        return self._next_index

    def get_points(self):
        # We do not have points for commands that are automatically added, 
        # because we add them when they arrive.
        return []

    def add_commands(self):
        # Commands are added when they arrive, not in here.
        raise RuntimeError("RF sensor mission does not add commands")

    def _send_ack(self):
        """
        Send a "waypoint_ack" packet to the ground station.

        This packet mentions which waypoint index we expect next, which is 0
        when we do not have any waypoints anymore or the next unused index
        otherwise.
        """

        packet = Packet()
        packet.set("specification", "waypoint_ack")
        packet.set("next_index", self._next_index)
        packet.set("sensor_id", self._rf_sensor.id)

        self._rf_sensor.enqueue(packet, to=0)

    def _clear_waypoints(self, packet):
        """
        Clear the mission waypoints after receiving a "waypoint_clear" packet.
        """

        if self._rf_sensor.id != packet.get("to_id"):
            # Ignore packets not meant for us.
            return

        self.clear_mission()
        # Add a takeoff command for flying vehicles that use it.
        self.add_takeoff()
        self._next_index = 0
        self._waypoints_complete = False
        self._point = None
        self._send_ack()

    def _add_waypoint(self, packet):
        """
        Add a waypoint to the mission based on a "waypoint_add" packet.

        The packet must have the RF sensor ID in the "to_id" field and the
        index must be the next waypoint index; otherwise, the waypoint is not
        added to the vehicle's waypoints.
        """

        if self._rf_sensor.id != packet.get("to_id"):
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
        waypoint_type = Waypoint_Type(packet.get("type"))
        wait_id = packet.get("wait_id")
        wait_count = packet.get("wait_count")

        # Create location waypoints based on the type and additional data. 
        # `add_waypoint` handles any further conversions of the provided 
        # waypoints from the `Waypoint` object.
        location = self.geometry.make_location(latitude, longitude, altitude)
        waypoint = Waypoint.create(self.environment.get_import_manager(),
                                   waypoint_type, self._rf_sensor.id,
                                   self.geometry, location,
                                   previous_location=self._point,
                                   wait_id=wait_id, wait_count=wait_count)

        required_sensors = waypoint.get_required_sensors()
        for point in waypoint.get_points():
            self.add_waypoint(point, required_sensors)

        self._next_index += 1
        self._point = location
        self._send_ack()
