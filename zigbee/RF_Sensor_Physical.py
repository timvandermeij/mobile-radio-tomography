# Core imports
import time

# Package imports
from ..core.USB_Manager import USB_Manager
from NTP import NTP
from RF_Sensor import RF_Sensor

# pylint: disable=abstract-method
class RF_Sensor_Physical(RF_Sensor):
    """
    Base class for all physical RF sensors.

    In addition to the `RF_Sensor` base class, this class takes care of
    working with the USB manager and other physical RF sensor characteristics.
    """

    def __init__(self, arguments, thread_manager, location_callback,
                 receive_callback, valid_callback, usb_manager=None):
        """
        Initialize the physical RF sensor.

        The `usb_manager` must be a `USB_Manager` object. It is used for
        connecting to physical RF sensors.

        Classes that inherit this base class may extend this method.
        """

        super(RF_Sensor_Physical, self).__init__(arguments, thread_manager,
                                                 location_callback, receive_callback,
                                                 valid_callback)

        if not isinstance(usb_manager, USB_Manager):
            raise TypeError("The USB manager must be a `USB_Manager` object")

        self._usb_manager = usb_manager

        self._synchronized = False
        self._discovery_callback = None

        self._ntp = NTP(self)
        self._ntp_delay = self._settings.get("ntp_delay")

    def discover(self, callback):
        """
        Discover all RF sensors in the network. The `callback` function is
        called when an RF sensor reports its identity.

        Classes that inherit this base class must extend this method.
        """

        super(RF_Sensor_Physical, self).discover(callback)

        self._discovery_callback = callback

    def _synchronize(self):
        """
        Synchronize the clock with the ground station's clock before
        sending messages. This avoids clock skew caused by the fact that
        the Raspberry Pi devices do not have an onboard real time clock.
        """

        if self._id > 0 and self._settings.get("synchronize"):
            while not self._synchronized:
                self._ntp.start()
                time.sleep(self._ntp_delay)
