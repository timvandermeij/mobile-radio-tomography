import math
from dronekit import Command, Locations, LocationGlobal, LocationGlobalRelative, LocationLocal
from pymavlink import mavutil
from mock import patch, MagicMock
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..trajectory.Servo import Servo
from ..vehicle.Mock_Vehicle import Mock_Vehicle, CommandSequence, MockAttitude, VehicleMode, GlobalMessage
from vehicle import VehicleTestCase

class TestVehicleMockVehicle(VehicleTestCase):
    def setUp(self):
        self.set_arguments([], vehicle_class="Mock_Vehicle")
        super(TestVehicleMockVehicle, self).setUp()
        self._message_listener_mock = MagicMock()

        @self.vehicle.on_message('*')
        def listener(vehicle, name, msg):
            self._message_listener_mock(vehicle, name, msg)

    def test_flush(self):
        # The `flush` method does not do anything.
        self.vehicle.flush()

    def test_interface_mode(self):
        # Test that the mode-related properties work as expected.
        self.assertTrue(self.vehicle.use_simulation)
        self.assertFalse(self.vehicle.armed)
        with patch.object(Mock_Vehicle, "update_location") as update_mock:
            update_mock.reset_mock()
            self.assertEqual(self.vehicle.mode.name, "SIMULATED")
            self.vehicle.mode = VehicleMode("TEST")
            self.assertEqual(self.vehicle.mode.name, "TEST")
            update_mock.assert_called_once_with()

    def test_check_arming(self):
        self.assertTrue(self.vehicle.check_arming())
        self.assertEqual(self.vehicle.mode.name, "GUIDED")

    def test_interface_speed(self):
        # Test that the speed-related properties work as expected.
        with patch.object(Mock_Vehicle, "update_location") as update_mock:
            self.assertEqual(self.vehicle.speed, 0.0)
            self.vehicle.speed = 1.0
            self.assertEqual(self.vehicle.velocity, [0.0, 0.0, 0.0])
            self.vehicle.velocity = [0.33, 1.0, 0.5]
            self.assertEqual(self.vehicle.speed, 0.0)
            update_mock.assert_any_call()

            self.assertEqual(self.vehicle.airspeed, 0.0)
            self.assertEqual(self.vehicle.groundspeed, 0.0)

    def test_attitude(self):
        # Test that the attitude-related properties work as expected.
        with patch.object(Mock_Vehicle, "update_location") as update_mock:
            attitude = self.vehicle.attitude
            self.assertIsInstance(attitude, MockAttitude)
            self.assertEqual(attitude.vehicle, self.vehicle)
            update_mock.assert_called_once_with()

            update_mock.reset_mock()
            self.assertEqual(attitude.pitch, 0.0)
            self.assertEqual(attitude.yaw, 0.0)
            self.assertEqual(attitude.roll, 0.0)
            update_mock.assert_any_call()

            update_mock.reset_mock()
            with patch.object(Mock_Vehicle, "set_target_attitude") as target_mock:
                attitude.pitch = 2.0
                target_mock.assert_called_once_with(2.0, None, None)
                target_mock.reset_mock()
                attitude.yaw = 1.0
                target_mock.assert_called_once_with(None, 1.0, None)
                target_mock.reset_mock()
                attitude.roll = 0.01
                target_mock.assert_called_once_with(None, None, 0.01)
                update_mock.assert_any_call()

            with self.assertRaises(TypeError):
                self.vehicle.attitude = (1, 2, 3)

            update_mock.reset_mock()
            new_attitude = MockAttitude(0.1, 0.2, 0.3)
            self.vehicle.attitude = new_attitude
            self.assertEqual(new_attitude.vehicle, self.vehicle)
            update_mock.assert_not_called()

            self.assertFalse(attitude == new_attitude)
            self.assertFalse(new_attitude == (0.1, 0.2, 0.3))
            self.assertTrue(new_attitude == MockAttitude(0.1, 0.2, 0.3))

    def test_location(self):
        # Test that the location property works as expected.
        with patch.object(Mock_Vehicle, "update_location") as update_mock:
            location = self.vehicle.location
            self.assertIsInstance(location, Locations)
            self.assertEqual(location.local_frame, LocationLocal(0.0, 0.0, 0.0))
            # The global frame does not have an altitude component set because 
            # no home location has been set.
            self.assertEqual(location.global_frame,
                             LocationGlobal(0.0, 0.0, None))
            self.assertEqual(location.global_relative_frame,
                             LocationGlobalRelative(0.0, 0.0, 0.0))
            update_mock.assert_called_once_with()

            # Updating the location works (via dronekit's Locations and the 
            # message listeners).
            self.vehicle.location = LocationGlobalRelative(1.0, 2.0, -3.0)
            self.assertEqual(self.vehicle.location.global_relative_frame,
                             LocationGlobalRelative(1.0, 2.0, -3.0))
            msg = GlobalMessage(1.0 * 1e7, 2.0 * 1e7, -3.0 * 1000, -3.0 * 1000)
            self._message_listener_mock.assert_called_once_with(self.vehicle, 'GLOBAL_POSITION_INT', msg)

            # Recursive location setting is detected.
            listener = lambda vehicle, attribute, value: vehicle.set_location(9.9, 8.8, 7.7)
            self.vehicle.add_attribute_listener('location', listener)
            with self.assertRaises(RuntimeError):
                self.vehicle.location = LocationGlobal(5.0, 4.0, -2.0)

    def test_set_location(self):
        # Setting a location via a distance update works similar to the 
        # location setter.
        self.vehicle.set_location(3.4, 5.6, 8.7)
        self.assertEqual(self.vehicle.location.global_relative_frame,
                         LocationGlobalRelative(3.4, 5.6, 8.7))
        self.assertEqual(self.vehicle.location.local_frame,
                         LocationLocal(3.4, 5.6, -8.7))

    def test_notify_message_listeners(self):
        self.vehicle.notify_message_listeners("FOO", "Hello world!")
        self._message_listener_mock.assert_called_once_with(self.vehicle, "FOO",
                                                            "Hello world!")

    def test_on_message(self):
        bar_message_listener_mock = MagicMock()
        @self.vehicle.on_message("BAR")
        def listener(vehicle, name, msg):
            bar_message_listener_mock(vehicle, name, msg)

        self.vehicle.notify_message_listeners("BAR", [1, 2, 3])
        bar_message_listener_mock.assert_called_once_with(self.vehicle, "BAR",
                                                          [1, 2, 3])
        self._message_listener_mock.assert_called_once_with(self.vehicle, "BAR",
                                                            [1, 2, 3])

    def test_home_location(self):
        # Test that the home location property works as expected.

        # Normal geometry and spherical geometry have different home location 
        # types.
        self.assertEqual(self.vehicle.home_location,
                         LocationLocal(0.0, 0.0, 0.0))
        with patch.object(self.vehicle, "_geometry", spec=Geometry_Spherical):
            self.assertEqual(self.vehicle.home_location,
                             LocationGlobal(0.0, 0.0, 0.0))

        # Normal geometry does not expose the global location when it is 
        # changed, but only a local location.
        self.vehicle.home_location = LocationGlobal(4.2, 5.7, 9.0)
        self.assertEqual(self.vehicle.home_location,
                         LocationLocal(0.0, 0.0, 0.0))

        # Spherical geometry does expose the new global location.
        with patch.object(self.vehicle, "_geometry", spec=Geometry_Spherical):
            self.vehicle.home_location = LocationGlobal(4.2, 5.7, 9.0)
            self.assertEqual(self.vehicle.home_location,
                             LocationGlobal(4.2, 5.7, 9.0))

    def test_set_yaw(self):
        with patch.object(Mock_Vehicle, "set_target_attitude") as target_mock:
            self.vehicle.set_yaw(90)
            target_mock.assert_called_once_with(yaw=0.5 * math.pi,
                                                yaw_direction=1)

            self.vehicle.attitude = MockAttitude(0.0, math.pi, 0.0)
            target_mock.reset_mock()
            self.vehicle.set_yaw(45, relative=True, direction=-1)
            target_mock.assert_called_once_with(yaw=math.pi + 0.25 * math.pi,
                                                yaw_direction=-1)

    def test_set_servo(self):
        servo_mock = MagicMock(spec=Servo)
        self.vehicle.set_servo(servo_mock, 1000)
        servo_mock.set_current_pwm.assert_called_once_with(1000)

    def test_simple_takeoff(self):
        # Check that the simple_takeoff method works.
        self.vehicle.armed = True
        with patch.object(Mock_Vehicle, "set_target_location") as target_mock:
            # Taking off does not occur when the vehicle is not in guided mode.
            self.vehicle.simple_takeoff(5.5)
            target_mock.assert_not_called()

            self.vehicle.mode = VehicleMode("GUIDED")
            self.vehicle.simple_takeoff(1.1)
            target_mock.assert_called_once_with(alt=1.1, takeoff=True)

    def test_simple_goto(self):
        # Check that the simple_goto method works.
        self.vehicle.armed = True
        with patch.object(Mock_Vehicle, "set_target_location") as target_mock:
            target_mock.reset_mock()
            loc = LocationLocal(1.2, 3.4, -4.5)
            self.vehicle.simple_goto(loc)
            target_mock.assert_called_once_with(location=loc)

    def test_commands(self):
        # Test that the command sequence is correct as needed by the 
        # MAVLink_Vehicle interface.
        commands = self.vehicle.commands
        self.assertIsInstance(commands, CommandSequence)

        # The required methods exist but do not influence anything.
        commands.download()
        commands.upload()
        commands.wait_ready()

        self.assertEqual(commands.next, 0)
        self.assertEqual(commands.count, 0)
        with self.assertRaises(IndexError):
            dummy = commands[0]

        with patch.object(Mock_Vehicle, "set_target_location") as target_mock:
            loc = LocationLocal(5.5, 6.4, -7.3)
            commands.goto(loc)
            self.assertEqual(self.vehicle.mode.name, "GUIDED")
            target_mock.assert_called_once_with(location=loc)

            # Taking off does not happen when the vehicle is not armed.
            target_mock.reset_mock()
            commands.takeoff(123)
            target_mock.assert_not_called()

            self.vehicle.armed = True
            commands.takeoff(4.5)
            target_mock.assert_called_once_with(alt=4.5, takeoff=True)

        commands.add('foo')
        commands.add(None)
        commands.add('bar')
        self.assertEqual(commands.count, 3)
        self.assertEqual(commands[commands.next], 'foo')
        with patch.object(Mock_Vehicle, "clear_target_location") as target_mock:
            with patch.object(Mock_Vehicle, "update_location") as update_mock:
                commands.next = 1
                update_mock.assert_called_once_with()
                target_mock.assert_called_once_with()
                self.assertIsNone(commands[commands.next])
                self.assertEqual(commands[2], 'bar')

        commands.clear()
        self.assertEqual(commands.count, 0)

    def test_parse_command(self):
        # Ignore unsupported commands
        self.vehicle._parse_command(None)
        self.assertEqual(self.vehicle.commands.next, 1)

        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL,
                      mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                      3.4, 2.3, 1.2)
        self.vehicle._parse_command(cmd)
        self.assertEqual(self.vehicle.commands.next, 2)

        # Waypoint commands set a target location.
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                      3.4, 2.3, 1.2)
        with patch.object(Mock_Vehicle, "set_target_location") as target_mock:
            self.vehicle._parse_command(cmd)
            target_mock.assert_called_once_with(lat=3.4, lon=2.3, alt=1.2)

        # Loiter commands set the target location to mark indefinite wait.
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM, 0, 0, 0, 0, 0,
                      0, 0, 0, 0)
        self.vehicle._parse_command(cmd)
        self.assertFalse(self.vehicle._target_location)

        # Takeoff commands set a target takeoff location, unless the vehicle 
        # has already taken off.
        cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                      mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0,
                      0, 0, 45.0)
        with patch.object(Mock_Vehicle, "set_target_location") as target_mock:
            self.vehicle._parse_command(cmd)
            target_mock.assert_called_once_with(alt=45.0, takeoff=True)

        self.vehicle._takeoff = True
        self.vehicle._parse_command(cmd)
        self.assertEqual(self.vehicle.commands.next, 3)

    def test_set_target_attitude(self):
        self.vehicle.set_target_attitude()
        self.assertEqual(self.vehicle._target_attitude,
                         MockAttitude(0.0, 0.0, 0.0, self.vehicle))

        self.vehicle.set_target_attitude(yaw=math.pi, yaw_direction=1)
        self.assertEqual(self.vehicle._target_attitude,
                         MockAttitude(0.0, math.pi, 0.0, self.vehicle))

    def test_set_target_location(self):
        loc = LocationGlobalRelative(1.0, 1.0, 5.6)

        # Changing location has no effect when the vehicle has not taken off.
        self.vehicle.set_target_location(location=loc)
        self.assertIsNone(self.vehicle._target_location)

        # Takeoff locations work as expected.
        self.vehicle.set_target_location(alt=7.8, takeoff=True)
        self.assertTrue(self.vehicle._takeoff)
        self.assertEqual(self.vehicle._target_location,
                         LocationLocal(0.0, 0.0, -7.8))

        self.vehicle.set_target_location()
        self.assertEqual(self.vehicle._target_location,
                         LocationLocal(0.0, 0.0, 0.0))

        with patch.object(self.vehicle, "_geometry", spec=Geometry_Spherical) as geometry_mock:
            self.vehicle.set_target_location(location=loc)
            self.assertEqual(self.vehicle._target_location, loc)
            geometry_mock.get_angle.assert_called_once_with(self.vehicle.location, loc)
            self.assertEqual(geometry_mock.angle_to_bearing.call_count, 1)
            self.assertEqual(self.vehicle._target_attitude._yaw,
                             geometry_mock.angle_to_bearing.return_value)

    def test_clear_target_location(self):
        self.vehicle.set_target_location(alt=6.5, takeoff=True)
        self.vehicle.clear_target_location()
        self.assertIsNone(self.vehicle._target_location)

    def test_pause(self):
        with patch.object(Mock_Vehicle, "_get_delta_time") as delta_mock:
            self.vehicle.check_arming()
            self.vehicle.armed = True

            self.vehicle.pause()
            self.assertEqual(self.vehicle.mode.name, "PAUSE")

            self.vehicle.update_location()
            delta_mock.assert_not_called()

    def test_update_location_speed(self):
        with patch.object(Mock_Vehicle, "_get_delta_time", return_value=(1.0, 1234567890.123)) as delta_mock:
            self.vehicle.update_location()
            delta_mock.assert_not_called()

            self.vehicle.check_arming()
            self.vehicle.armed = True
            self.vehicle.speed = 1.5
            self.vehicle.simple_takeoff(2.0)

            # Takeoff works stepwise.
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(0.0, 0.0, -1.5))
            delta_mock.assert_called_once_with()

            delta_mock.reset_mock()
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(0.0, 0.0, -2.0))
            delta_mock.assert_called_once_with()

            self.vehicle.clear_target_location()
            self.vehicle.velocity = [2.5, 0.0, 0.0]
            delta_mock.reset_mock()

            # Velocity step works.
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(2.5, 0.0, -2.0))
            delta_mock.assert_called_once_with()

    def test_update_location_goto(self):
        with patch.object(Mock_Vehicle, "_get_delta_time", return_value=(1.0, 1234567890.123)) as delta_mock:
            self.vehicle.check_arming()
            self.vehicle.armed = True
            self.vehicle._takeoff = True
            self.vehicle.speed = 7.5

            # Goto snaps to the target location if it is reachable in one step.
            loc = LocationLocal(5.0, 0.0, 0.0)
            self.vehicle.set_target_location(location=loc)
            delta_mock.reset_mock()
            self.assertEqual(self.vehicle.location.local_frame, loc)
            delta_mock.assert_called_once_with()

    def test_update_location_goto_spherical(self):
        with patch.object(Mock_Vehicle, "_get_delta_time", return_value=(1.0, 1234567890.123)):
            loc = LocationGlobalRelative(0.01, 0.0, 1.0)
            parameters = {
                "spec": Geometry_Spherical,
                "get_location_meters.return_value": loc,
                "diff_location_meters.return_value": (0.01, 0.0, 1.0)
            }
            with patch.object(self.vehicle, "_geometry", **parameters):
                self.vehicle.check_arming()
                self.vehicle.armed = True
                self.vehicle._takeoff = True
                self.vehicle.speed = 7.5

                # Goto snaps to the target location if it is reachable in one 
                # step.
                self.vehicle.set_target_location(location=loc)
                self.assertEqual(self.vehicle.location.global_relative_frame, loc)

    def test_update_location_auto(self):
        with patch.object(Mock_Vehicle, "_get_delta_time", return_value=(1.0, 1234567890.123)) as delta_mock:
            self.vehicle.check_arming()
            self.vehicle.armed = True
            self.vehicle._takeoff = True

            self.vehicle.speed = 5.0
            self.vehicle._attitude_speed = [10.0, 45.0, 10.0]
            self.vehicle.mode = VehicleMode("AUTO")
            cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                          mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                          2.0, 0.0, 0.0)
            self.vehicle.commands.add(cmd)

            cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                          mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                          2.0, 10.0, 0.0)
            self.vehicle.commands.add(cmd)

            cmd = Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                          mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0,
                          2.0, 20.0, 10.0)
            self.vehicle.commands.add(cmd)

            # First call to update_location: command parsing
            delta_mock.reset_mock()
            self.vehicle.update_location()
            self.assertEqual(self.vehicle.commands.next, 0)
            self.assertEqual(self.vehicle._target_location,
                             LocationLocal(2.0, 0.0, 0.0))
            delta_mock.assert_called_once_with()

            # Second call (via location): reached first location
            delta_mock.reset_mock()
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(2.0, 0.0, 0.0))
            delta_mock.assert_called_once_with()

            # Third call (via next): target location is reset
            delta_mock.reset_mock()
            self.vehicle.commands.next = self.vehicle.commands.next + 1
            self.assertIsNone(self.vehicle._target_location)
            delta_mock.assert_called_once_with()

            # Fourth call to update_location: command parsing
            delta_mock.reset_mock()
            self.vehicle.update_location()
            self.assertEqual(self.vehicle.commands.next, 1)
            self.assertEqual(self.vehicle._target_location,
                             LocationLocal(2.0, 10.0, 0.0))
            delta_mock.assert_called_once_with()

            # Fifth call (via attitude): rotating attitude
            delta_mock.reset_mock()
            self.assertEqual(self.vehicle.attitude,
                             MockAttitude(0.0, 0.25*math.pi, 0.0, self.vehicle))
            delta_mock.assert_called_once_with()

            # Sixth call (via attitude): rotated attitude and going to second 
            # location
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(2.0, 5.0, 0.0))
            self.assertEqual(self.vehicle.attitude,
                             MockAttitude(0.0, 0.5*math.pi, 0.0, self.vehicle))

            # Reached second location
            delta_mock.reset_mock()
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(2.0, 10.0, 0.0))
            delta_mock.assert_called_once_with()

            # Going to third location and reaching it at correct altitude
            self.vehicle.commands.next = self.vehicle.commands.next + 1
            self.vehicle.update_location()
            self.assertEqual(self.vehicle.location.local_frame.east, 15.0)
            self.vehicle.update_location()
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(2.0, 20.0, -10.0))

    def test_get_delta_time(self):
        self.vehicle._update_time = 1234567890.25
        with patch("time.time", return_value=1234567890.5):
            diff, new_time = self.vehicle._get_delta_time()
            self.assertEqual(diff, 0.25)
            self.assertEqual(new_time, 1234567890.5)
