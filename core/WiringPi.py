class WiringPi(object):
    """
    Wrapper singleton for the wiringpi module.

    This is required because the setup function of wiringPi can only be called
    once. This class also ensures that the wiringpi functions can only be used
    when run on a Raspberry Pi device.
    """

    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            try:
                import RPi.GPIO as GPIO
                import wiringpi
            except (ImportError, RuntimeError):
                GPIO = None
                wiringpi = None

            if GPIO is not None:
                wiringpi.wiringPiSetupPhys()

            cls.singleton = super(WiringPi, cls).__new__(cls)
            cls.singleton._is_raspberry_pi = GPIO is not None
            cls.singleton._module = wiringpi

        return cls.singleton

    @property
    def is_raspberry_pi(self):
        return self._is_raspberry_pi

    @property
    def module(self):
        return self._module
