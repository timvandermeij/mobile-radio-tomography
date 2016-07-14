from dronekit import LocationLocal
from ..geometry.Geometry import Geometry
from ..waypoint.Waypoint import Waypoint_Type
from ..waypoint.Waypoint_Wait import Waypoint_Wait
from geometry import LocationTestCase

class TestWaypointWait(LocationTestCase):
    def setUp(self):
        super(TestWaypointWait, self).setUp()

        self.geometry = Geometry()
        self.location = LocationLocal(0.0, 10.0, 0.0)
        self.waypoint = Waypoint_Wait(1, self.geometry, self.location,
                                      wait_id=2, wait_count=5)

    def test_name(self):
        self.assertEqual(self.waypoint.name, Waypoint_Type.WAIT)

    def test_get_points(self):
        points = self.waypoint.get_points()
        self.assertEqual(len(points), 5)
        self.assertEqual(points[0], LocationLocal(0.0, 2.0, 0.0))
        self.assertEqual(points[1], LocationLocal(0.0, 4.0, 0.0))
        self.assertEqual(points[2], LocationLocal(0.0, 6.0, 0.0))
        self.assertEqual(points[3], LocationLocal(0.0, 8.0, 0.0))
        self.assertEqual(points[4], LocationLocal(0.0, 10.0, 0.0))

    def test_get_required_sensors(self):
        self.assertEqual(self.waypoint.get_required_sensors(), [2])

    def test_initialization_previous_waypoint(self):
        waypoint = Waypoint_Wait(1, self.geometry, self.location,
                                 previous_location=LocationLocal(10, 10, 0),
                                 wait_id=0, wait_count=2)

        points = waypoint.get_points()
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0], LocationLocal(5.0, 10.0, 0.0))
        self.assertEqual(points[1], LocationLocal(0.0, 10.0, 0.0))

        self.assertIsNone(waypoint.get_required_sensors())
