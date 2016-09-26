from dronekit import LocationLocal
from mock import MagicMock
from ..geometry.Geometry import Geometry
from ..location.Line_Follower import Line_Follower_Direction
from ..vehicle.Vehicle import Vehicle
from ..waypoint.Waypoint import Waypoint_Type
from ..waypoint.Waypoint_Home import Waypoint_Home
from geometry import LocationTestCase

class TestWaypointHome(LocationTestCase):
    def setUp(self):
        super(TestWaypointHome, self).setUp()

        self.geometry = Geometry()
        self.location = LocationLocal(1.2, 3.4, -5.6)
        self.direction = Line_Follower_Direction.DOWN
        self.waypoint = Waypoint_Home(1, self.geometry, self.location,
                                      home_direction=self.direction)

    def test_name(self):
        self.assertEqual(self.waypoint.name, Waypoint_Type.HOME)

    def test_home_direction(self):
        self.assertEqual(self.waypoint.home_direction, self.direction)

    def test_get_points(self):
        self.assertEqual(self.waypoint.get_points(), [])

    def test_update_vehicle(self):
        # The `vehicle` parameter must be a vehicle.
        with self.assertRaises(TypeError):
            self.waypoint.update_vehicle(self.geometry)

        vehicle_mock = MagicMock(spec_set=Vehicle)
        self.waypoint.update_vehicle(vehicle_mock)
        yaw = self.direction.yaw
        vehicle_mock.set_home_state.assert_called_once_with(self.location,
                                                            yaw=yaw)
