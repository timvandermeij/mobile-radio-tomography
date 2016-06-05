import sys
import unittest
from mock import patch, MagicMock

class WiringPiTestCase(unittest.TestCase):
    """
    Test case class for tests that make use of modules that import WiringPi,
    directly or indirectly. This is required to set up and unload the wiringpi
    module correctly. This class also provides module mocks for RPi.GPIO as well
    as wiringpi itself.
    """

    def __init__(self, *a, **kw):
        super(WiringPiTestCase, self).__init__(*a, **kw)

        # Disable the RPi.GPIO patcher by default, so test cases have to opt-in 
        # to run Raspberry Pi-specific tests.
        self._rpi_patch = False

    def set_rpi_patch(self, rpi_patch=True):
        self._rpi_patch = rpi_patch

    def setUp(self):
        super(WiringPiTestCase, self).setUp()

        # We need to mock the RPi.GPIO module as it is only available
        # on Raspberry Pi devices and these tests run on a PC.
        self.rpi_gpio_mock = MagicMock()
        self.wiringpi_mock = MagicMock()

        if self._rpi_patch:
            modules = {
                'RPi': self.rpi_gpio_mock,
                'RPi.GPIO': self.rpi_gpio_mock.GPIO,
                'wiringpi': self.wiringpi_mock
            }

            self._rpi_patcher = patch.dict('sys.modules', modules)
            self._rpi_patcher.start()
        else:
            self._rpi_patcher = None
        
    def tearDown(self):
        super(WiringPiTestCase, self).tearDown()

        from ..core.WiringPi import WiringPi
        WiringPi.singleton = None

        if self._rpi_patcher is not None:
            self._rpi_patcher.stop()

        # Unload the module from the sys.modules cache so that later imports 
        # have to check whether RPi.GPIO exists (as a mock) or not.
        package = __package__.split('.')[0] + ".core.WiringPi"
        if package in sys.modules:
            del sys.modules[package]

class TestCoreWiringPi(WiringPiTestCase):
    def setUp(self):
        # Enable the RPi.GPIO patcher.
        self.set_rpi_patch()
        super(TestCoreWiringPi, self).setUp()

    def test_raspberry_pi(self):
        from ..core.WiringPi import WiringPi, GPIO
        # Mock import means we have an RPi GPIO variable
        self.assertEqual(GPIO, self.rpi_gpio_mock.GPIO)

        # Singleton creation ensures we always get the same object.
        self.assertIsNone(WiringPi.singleton)
        wiringpi = WiringPi()
        self.assertEqual(WiringPi.singleton, wiringpi)
        other_wiringpi = WiringPi()
        self.assertEqual(wiringpi, other_wiringpi)

        # Singleton creation ensures we call the wiringPi setup function once.
        self.wiringpi_mock.wiringPiSetupPhys.assert_called_once_with()

        # RPi GPIO mock means the module assumes we are on a Raspberry Pi.
        self.assertTrue(wiringpi.is_raspberry_pi)
        self.assertEqual(wiringpi.module, self.wiringpi_mock)

    def test_not_raspberry_pi(self):
        # Mark as nonexistent module
        sys.modules["RPi.GPIO"] = None
        from ..core.WiringPi import WiringPi, GPIO

        # Import error means the RPi GPIO variable is None. 
        self.assertIsNone(GPIO)

        # Singleton creation ensures we always get the same object.
        self.assertIsNone(WiringPi.singleton)
        wiringpi = WiringPi()
        self.assertEqual(WiringPi.singleton, wiringpi)
        other_wiringpi = WiringPi()
        self.assertEqual(wiringpi, other_wiringpi)

        # Import error means we do not call the wiringPi setup function.
        self.wiringpi_mock.wiringPiSetupPhys.assert_not_called()

        # Import error means the module assumes we are not on a Raspberry Pi.
        self.assertFalse(wiringpi.is_raspberry_pi)
        self.assertIsNone(wiringpi.module)
