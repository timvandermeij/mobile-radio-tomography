import serial
from mock import patch
from ..core.Threadable import Threadable
from ..trajectory.Servo import Servo
from vehicle_robot_vehicle import RobotVehicleTestCase

class TestVehicleRobotVehicleArduino(RobotVehicleTestCase):
    def setUp(self):
        self.set_arguments([
            "--motor-speed-pwms", "0", "2000", "--motor-speeds", "-0.6", "0.6",
            "--activate-delay", "0"
        ], vehicle_class="Robot_Vehicle_Arduino")
        self.set_rpi_patch()
        super(TestVehicleRobotVehicleArduino, self).setUp()

    def test_init(self):
        self.assertEqual(self.vehicle._speed_pwms, (0, 2000))
        self.assertEqual(self.vehicle._speeds, (-0.6, 0.6))
        self.assertEqual(len(self.vehicle._speed_servos), 2)
        for i in range(2):
            self.assertIsInstance(self.vehicle._speed_servos[i], Servo)

        self.assertIsInstance(self.vehicle._serial_connection, serial.Serial)
        self.assertEqual(self.vehicle._current_speed, (0, 0, True, True))

    def test_setup(self):
        with patch.object(self.vehicle, "_serial_connection") as serial_mock:
            self.vehicle.setup()

            serial_mock.reset_output_buffer.assert_called_once_with()

    def test_use_simulation(self):
        self.vehicle.setup()

        # Simulation is disabled when we have a working (patched) RPi.GPIO.
        # Certain mission and environment tests have test cases for enabled 
        # simulation.
        self.assertFalse(self.vehicle.use_simulation)

    @patch("thread.start_new_thread")
    def test_activate(self, thread_mock):
        with patch.object(Threadable, "activate"):
            self.vehicle.activate()
            # Reset signal is turned off on the DTR line.
            self.assertFalse(self.vehicle._serial_connection.dtr)
            self.assertEqual(self._ttl_device.readline(), "START\n")
            thread_mock.assert_any_call(self.vehicle._state_loop, ())

    def test_deactivate(self):
        with patch.object(self.vehicle, "set_speeds") as set_speeds_mock:
            with patch.object(Threadable, "deactivate"):
                self.vehicle.deactivate()
                set_speeds_mock.assert_called_once_with(0, 0)
                # Reset signal is at high level on the DTR line.
                self.assertTrue(self.vehicle._serial_connection.dtr)

    def test_pause(self):
        with patch.object(Threadable, "activate"):
            self.vehicle.activate()

        with patch.object(self.vehicle, "set_speeds") as set_speeds_mock:
            with patch.object(Threadable, "deactivate"):
                self.vehicle.pause()
                set_speeds_mock.assert_called_once_with(0, 0)
                # Reset signal is at low level on the DTR line, so not 
                # resetting in this case.
                self.assertFalse(self.vehicle._serial_connection.dtr)

    @patch.object(serial.Serial, "write")
    def test_set_speeds(self, write_mock):
        # Changing the speeds to the current speed does not write anything.
        self.vehicle.set_speeds(0, 0, True, True)
        write_mock.assert_not_called()

        self.vehicle.set_speeds(0.3, 0.15,
                                left_forward=False, right_forward=True)
        self.assertEqual(self.vehicle._current_speed, (0.3, 0.15, False, True))
        write_mock.assert_called_once_with("500 1250\n")
