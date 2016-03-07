class Interval(object):
    """
    Small interval range specification.
    """

    def __init__(self, minimum, maximum=None):
        if isinstance(minimum, (list,tuple)):
            if len(minimum) != 2:
                raise ValueError("Must be given an interval specification")
            if maximum is not None:
                raise ValueError("Cannot give both a sequence type and a maximum")

            minimum, maximum = minimum

        self.min = minimum
        self.max = maximum

    @property
    def diff(self):
        return self.max - self.min

class Servo(object):
    """
    Servo class that handles current PWM measurements and performs calculations
    to and from PWM values.
    """

    def __init__(self, pin, values, pwm=None):
        """
        Initialize a servo to work on the given `pin` integer.

        The given `values` is a tuple containing minimum and maximum values,
        such as servo angles, camera distances or motor speeds depending on
        the use of the servo. The `pwm` is a similar tuple for the PWM minimum
        and maximum values. By default, `pwm` is set to an interval [1000,2000).
        """

        self.pin = int(pin)
        # The values to be converted to and from PWMs, such as servo angles or 
        # motor speeds.
        self._values = Interval(values)

        if pwm is None:
            self.pwm = Interval(1000,2000)
        else:
            self.pwm = Interval(pwm)

        self._pwm_factor = self.pwm.diff / float(self._values.diff)
        self._value_factor = self._values.diff / float(self.pwm.diff)

        self._current_pwm = self.pwm.min

    def check_value(self, value):
        """
        Check whether the given `value` is within the value constraints.
        """
        return self._values.min <= value < self._values.max

    def get_pin(self):
        """
        Get the servo's pin number.
        """
        return self.pin

    def get_pwm(self, value=None):
        """
        Get the PWM of a given `value`, or the current PWM value if no value is given.
        """
        if value is None:
            return self._current_pwm

        return self.pwm.min + self._pwm_factor * (value - self._values.min)

    def set_current_pwm(self, pwm):
        """
        Store the given `pwm` as the current PWM value.
        """
        self._current_pwm = pwm

    def get_value(self, pwm=None):
        """
        Calculate the value belonging to a given `pwm`, or the current PWM if none is given.
        """
        if pwm is None:
            pwm = self._current_pwm

        return self._values.min + self._value_factor * (pwm - self.pwm.min)
