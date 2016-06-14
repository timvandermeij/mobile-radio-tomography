import math
from dronekit import Locations, LocationGlobal, LocationGlobalRelative, LocationLocal
from mock import patch, MagicMock
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..trajectory.Servo import Servo
from ..vehicle.Mock_Vehicle import Mock_Vehicle, CommandSequence, MockAttitude, VehicleMode
from vehicle import VehicleTestCase

class TestVehicleMockVehicle(VehicleTestCase):
    def setUp(self):
        self.set_arguments([], vehicle_class="Mock_Vehicle")
        super(TestVehicleMockVehicle, self).setUp()

    def test_interface_mode(self):
        # Test that the mode-related properties work as expected.
        self.assertTrue(self.vehicle.use_simulation)
        self.assertIsInstance(self.vehicle.commands, CommandSequence)
        self.assertFalse(self.vehicle.armed)
        with patch.object(Mock_Vehicle, "update_location") as update_mock:
            update_mock.reset_mock()
            self.assertEqual(self.vehicle.mode.name, "SIMULATED")
            self.vehicle.mode = VehicleMode("TEST")
            self.assertEqual(self.vehicle.mode.name, "TEST")
            update_mock.assert_called_once_with()

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

    def test_interface_attitude(self):
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

    def test_interface_location(self):
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

            # Setting a location via a distance update works similarly.
            self.vehicle.set_location(3.4, 5.6, 8.7)
            self.assertEqual(self.vehicle.location.global_relative_frame,
                             LocationGlobalRelative(3.4, 5.6, 8.7))
            self.assertEqual(self.vehicle.location.local_frame,
                             LocationLocal(3.4, 5.6, -8.7))

            # Recursive location setting is detected.
            listener = lambda vehicle, attribute, value: vehicle.set_location(9.9, 8.8, 7.7)
            self.vehicle.add_attribute_listener('location', listener)
            with self.assertRaises(RuntimeError):
                self.vehicle.location = LocationGlobal(5.0, 4.0, -2.0)

    def test_interface_home_location(self):
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

    def test_interface_simple(self):
        # Check that the simple_takeoff and simple_goto methods work.
        self.vehicle.armed = True
        with patch.object(Mock_Vehicle, "set_target_location") as target_mock:
            # Taking off does not occur when the vehicle is not in guided mode.
            self.vehicle.simple_takeoff(5.5)
            target_mock.assert_not_called()

            self.vehicle.mode = VehicleMode("GUIDED")
            self.vehicle.simple_takeoff(1.1)
            target_mock.assert_called_once_with(alt=1.1, takeoff=True)

            target_mock.reset_mock()
            loc = LocationLocal(1.2, 3.4, -4.5)
            self.vehicle.simple_goto(loc)
            target_mock.assert_called_once_with(location=loc)

    def test_command_sequence(self):
        # Test that the command sequence is correct as needed by the 
        # MAVLink_Vehicle interface.
        commands = self.vehicle.commands

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
