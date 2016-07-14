from dronekit import LocationLocal
from ..geometry.Geometry import Geometry
from ..waypoint.Waypoint import Waypoint_Type
from ..waypoint.Waypoint_Pass import Waypoint_Pass
from geometry import LocationTestCase

class TestWaypointPass(LocationTestCase):
    def setUp(self):
        super(TestWaypointPass, self).setUp()

        self.geometry = Geometry()
        self.location = LocationLocal(1.2, 3.4, -5.6)
        self.waypoint = Waypoint_Pass(1, self.geometry, self.location)

    def test_name(self):
        self.assertEqual(self.waypoint.name, Waypoint_Type.PASS)

    def test_get_points(self):
        points = self.waypoint.get_points()
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0], self.location)
