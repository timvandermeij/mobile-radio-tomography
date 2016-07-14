from dronekit import LocationLocal
from mock import patch
from ..core.Import_Manager import Import_Manager
from ..geometry.Geometry import Geometry
from ..waypoint.Waypoint import Waypoint, Waypoint_Type
from geometry import LocationTestCase

class TestWaypoint(LocationTestCase):
    def setUp(self):
        super(TestWaypoint, self).setUp()

        self.geometry = Geometry()
        self.location = LocationLocal(2.0, 3.0, -4.0)
        self.waypoint = Waypoint(1, self.geometry, self.location)

    @patch.object(Import_Manager, "load_class")
    def test_create(self, load_class_mock):
        import_manager = Import_Manager()
        geometry = Geometry()
        waypoint = Waypoint.create(import_manager, Waypoint_Type.WAIT, 42,
                                   geometry, LocationLocal(5.0, 6.0, -7.0),
                                   wait_id=2, wait_count=9)

        load_class_mock.assert_called_once_with("Waypoint_Wait",
                                                relative_module="waypoint")

        # The object is created with the appropriate arguments.
        self.assertEqual(waypoint, load_class_mock.return_value.return_value)
        self.assertEqual(load_class_mock.return_value.call_count, 1)
        args, kwargs = load_class_mock.return_value.call_args
        self.assertEqual(args[0], 42)
        self.assertEqual(args[1], geometry)
        self.assertEqual(args[2], LocationLocal(5.0, 6.0, -7.0))
        self.assertEqual(kwargs, {"wait_id": 2, "wait_count": 9})

    def test_interface(self):
        with self.assertRaises(NotImplementedError):
            dummy = self.waypoint.name

        self.assertEqual(self.waypoint.vehicle_id, 1)
        self.assertEqual(self.waypoint.location, self.location)

    def test_get_points(self):
        with self.assertRaises(NotImplementedError):
            self.waypoint.get_points()

    def test_get_required_sensors(self):
        with self.assertRaises(RuntimeError):
            self.waypoint.get_required_sensors()
