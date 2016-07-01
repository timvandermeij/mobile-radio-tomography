from dronekit import Command, LocationLocal, LocationGlobalRelative
from pymavlink import mavutil
from mock import patch, Mock, PropertyMock
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..vehicle.MAVLink_Vehicle import MAVLink_Vehicle
from vehicle import VehicleTestCase

class TestVehicleMockVehicle(VehicleTestCase):
    def setUp(self):
        self.set_arguments([], vehicle_class="MAVLink_Vehicle")
        super(TestVehicleMockVehicle, self).setUp()

    def test_interface(self):
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.commands
        with self.assertRaises(NotImplementedError):
            self.vehicle.flush()

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    @patch.object(MAVLink_Vehicle, "flush")
    def test_clear_waypoints(self, flush_mock, commands_mock):
        self.vehicle.clear_waypoints()
        commands_mock.return_value.clear.assert_called_once_with()
        commands_mock.return_value.download.assert_called_once_with()
        flush_mock.assert_called_once_with()

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_update_mission(self, commands_mock):
        self.vehicle.update_mission()
        commands_mock.return_value.upload.assert_called_once_with()
        commands_mock.return_value.wait_ready.assert_called_once_with()

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_add_takeoff(self, commands_mock):
        self.vehicle.add_takeoff(5.5)
        self.assertEqual(commands_mock.return_value.add.call_count, 1)
        args = commands_mock.return_value.add.call_args[0]
        self.assertIsInstance(args[0], Command)
        self.assertEqual(args[0].command, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF)
        self.assertEqual(args[0].z, 5.5)

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_add_waypoint(self, commands_mock):
        self.vehicle.add_waypoint(LocationLocal(1.0, 2.0, -3.0))
        self.assertEqual(commands_mock.return_value.add.call_count, 1)
        args = commands_mock.return_value.add.call_args[0]
        self.assertIsInstance(args[0], Command)
        self.assertEqual(args[0].command, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT)
        self.assertEqual(args[0].x, 1.0)
        self.assertEqual(args[0].y, 2.0)
        self.assertEqual(args[0].z, 3.0)

        commands_mock.reset_mock()
        self.vehicle.add_waypoint(LocationGlobalRelative(4.5, 6.7, 8.9))
        self.assertEqual(commands_mock.return_value.add.call_count, 1)

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_add_wait(self, commands_mock):
        self.vehicle.add_wait()
        self.assertEqual(commands_mock.return_value.add.call_count, 1)
        args = commands_mock.return_value.add.call_args[0]
        self.assertIsInstance(args[0], Command)
        self.assertEqual(args[0].command,
                         mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM)

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_is_wait(self, commands_mock):
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM, 0, 0, 0, 0, 0,
                      0, 0, 0, 0)
        commands_mock.return_value.configure_mock(
            __getitem__=Mock(return_value=cmd)
        )
        self.assertTrue(self.vehicle.is_wait())

        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0,
                      0, 0, 45.0)
        commands_mock.return_value.configure_mock(
            __getitem__=Mock(return_value=cmd)
        )
        self.assertFalse(self.vehicle.is_wait())

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_get_waypoint(self, commands_mock):
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM, 0, 0, 0, 0, 0,
                      0, 0, 0, 0)
        commands_mock.return_value.configure_mock(
            __getitem__=Mock(return_value=cmd)
        )

        self.assertIsNone(self.vehicle.get_waypoint(waypoint=1))

        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                      3.4, 2.3, 1.2)
        commands_mock.return_value.configure_mock(
            __getitem__=Mock(return_value=cmd)
        )

        self.assertEqual(self.vehicle.get_waypoint(),
                         LocationLocal(3.4, 2.3, -1.2))

        with patch.object(self.vehicle, "_geometry", new=Geometry_Spherical()):
            self.assertEqual(self.vehicle.get_waypoint(),
                             LocationGlobalRelative(3.4, 2.3, 1.2))

    @patch.object(MAVLink_Vehicle, "commands", new_callable=PropertyMock)
    def test_command_waypoints(self, commands_mock):
        next_mock = PropertyMock(return_value=1)
        type(commands_mock.return_value).next = next_mock
        self.assertEqual(self.vehicle.get_next_waypoint(), 1)

        self.vehicle.set_next_waypoint()
        next_mock.assert_any_call(2)
        self.vehicle.set_next_waypoint(waypoint=0)
        next_mock.assert_any_call(0)

        commands_mock.return_value.configure_mock(count=2)
        self.assertEqual(self.vehicle.count_waypoints(), 2)

    def test_is_current_location_valid(self):
        with patch.object(MAVLink_Vehicle, "location", new_callable=PropertyMock) as location_mock:
            loc = LocationLocal(1, 2, 3)
            location_mock.return_value.configure_mock(local_frame=loc)
            self.assertTrue(self.vehicle.is_current_location_valid())

            loc = LocationLocal(None, 2, 3)
            location_mock.return_value.configure_mock(local_frame=loc)
            self.assertFalse(self.vehicle.is_current_location_valid())

            with patch.object(self.vehicle, "_geometry", new=Geometry_Spherical()):
                loc = LocationGlobalRelative(4, 5, 6)
                location_mock.return_value.configure_mock(global_relative_frame=loc)
                self.assertTrue(self.vehicle.is_current_location_valid())

                loc = LocationGlobalRelative(6.7, 8.9, None)
                location_mock.return_value.configure_mock(global_relative_frame=loc)
                self.assertFalse(self.vehicle.is_current_location_valid())
