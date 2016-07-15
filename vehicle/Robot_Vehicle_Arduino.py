import time
from Robot_Vehicle import Robot_Vehicle
from ..trajectory.Servo import Servo

class Robot_Vehicle_Arduino(Robot_Vehicle):
    """
    Robot vehicle that is connected via a serial interface to an Arduino.

    To be used with the "zumo_serial" Arduino program.

    The Arduino passes through reflectance sensor measurements which are read by
    the `Line_Follower_Arduino` class, while the `Robot_Vehicle_Arduino` sends
    motor speeds to the Arduino that are passed through to the motor control.
    """

    _line_follower_class = "Line_Follower_Arduino"

    def __init__(self, arguments, geometry, import_manager, thread_manager, usb_manager):
        super(Robot_Vehicle_Arduino, self).__init__(arguments, geometry, import_manager,
                                                    thread_manager, usb_manager)

        self.settings = arguments.get_settings("vehicle_robot_arduino")

        self._activate_delay = self.settings.get("activate_delay")

        # PWM range for both motors (minimum and maximum values)
        self._speed_pwms = self.settings.get("motor_speed_pwms")
        # Speed range for both motors in m/s
        self._speeds = self.settings.get("motor_speeds")

        # Servo objects for tracking and converting speed PWM values. The pin 
        # numbers are dummy.
        self._speed_servos = [Servo(i, self._speeds, self._speed_pwms) for i in range(2)]

        self._serial_connection = usb_manager.get_ttl_device()
        self._current_speed = (0, 0, True, True)

    def setup(self):
        super(Robot_Vehicle_Arduino, self).setup()

        self._serial_connection.reset_output_buffer()

    @property
    def use_simulation(self):
        return not self._wiringpi.is_raspberry_pi

    def activate(self):
        super(Robot_Vehicle_Arduino, self).activate()

        # Send a DTR signal to turn on the Arduino via the RESET line. 
        # According to a forum post at 
        # http://forum.arduino.cc/index.php?topic=38981.msg287027#msg287027 and 
        # the ATmega328P datasheet, we need to send a low DTR to turn on the 
        # vehicle, and the pulse needs to be at least 2.5 microseconds to get 
        # through. We add more time for it to reset and start the serial 
        # connection, since that may take some time.
        self._serial_connection.dtr = False
        time.sleep(self._activate_delay)

        # Let the Arduino know that the serial connection is established and we 
        # want to arm the vehicle.
        self._serial_connection.write("START\n")
        self._serial_connection.flush()

    def _reset(self):
        # Turn off motors.
        self.set_speeds(0, 0)
        self._serial_connection.dtr = True

    def deactivate(self):
        self._reset()

        super(Robot_Vehicle_Arduino, self).deactivate()

    def pause(self):
        super(Robot_Vehicle_Arduino, self).pause()

        # If we are just halting, then only turn off the motors, not the 
        # connection.
        self.set_speeds(0, 0)

    def _format_speeds(self, left_speed, right_speed, left_forward, right_forward):
        output = ""

        parts = [(0, left_speed, left_forward), (1, right_speed, right_forward)]
        for i, speed, forward in parts:
            if not forward:
                speed = -speed

            pwm = self._speed_servos[i].get_pwm(speed)
            self._speed_servos[i].set_current_pwm(pwm)
            output += "{} ".format(int(pwm))

        return output.strip()

    def set_speeds(self, left_speed, right_speed, left_forward=True, right_forward=True):
        new_speed = (left_speed, right_speed, left_forward, right_forward)
        if self._current_speed == new_speed:
            # Avoid sending the same message multiple times after each other, 
            # since the Arduino will keep at the same speed until a different 
            # message appears.
            return

        self._current_speed = new_speed
        output = self._format_speeds(*new_speed)

        self._serial_connection.write("{}\n".format(output))
