# Core imports
import random
import socket
import time

# Package imports
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import RF_Sensor, DisabledException

class RF_Sensor_Simulator(RF_Sensor):
    """
    Simulated RF sensor, suitable for debugging and research.
    """

    def __init__(self, arguments, thread_manager, location_callback,
                 receive_callback, valid_callback, **kwargs):
        """
        Initialize the simulated RF sensor.

        Physical RF sensors use a keyword argument for the USB manager,
        but since simulated RF sensors do not use that, the keyword arguments
        are ignored. They are only added to keep the constructors equal for
        all RF sensor classes.
        """

        super(RF_Sensor_Simulator, self).__init__(arguments, thread_manager,
                                                  location_callback,
                                                  receive_callback,
                                                  valid_callback)

        # Simulated RF sensors immediately join the (virtual) network.
        self._joined = True

        # Simulated RF sensors have an IP address and a port for their socket.
        # This information combined with the ID forms the sensor's address.
        self._ip = self._settings.get("socket_ip")
        self._port = self._settings.get("socket_port")
        self._address = "{}:{}".format(self._ip, self._port + self._id)

        # Simulated RF sensors use a fixed buffer size for reading from the
        # socket connection.
        self._buffer_size = self._settings.get("buffer_size")

    @property
    def type(self):
        """
        Get the type of the RF sensor.

        The type is equal to the name of the settings group.
        """

        return "rf_sensor_simulator"

    def discover(self, callback):
        """
        Discover all RF sensors in the network. The `callback` function is
        called when an RF sensor reports its identity.
        """

        super(RF_Sensor_Simulator, self).discover(callback)

        for vehicle_id in xrange(1, self._number_of_sensors + 1):
            callback({
                "id": vehicle_id,
                "address": "{}:{}".format(self._ip, self._port + vehicle_id)
            })

    def _setup(self):
        """
        Setup the RF sensor by opening the connection to it.
        """

        self._connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._connection.bind((self._ip, self._port + self._id))
        self._connection.setblocking(0)

    def _loop_body(self):
        """
        Body of the sensor loop.

        This is extracted into a separate method to make testing easier, as well
        as for keeping the `_loop` implementation in the base class.
        """

        # If the sensor has been activated, this loop will only send
        # enqueued custom packets. If the sensor has been started, we
        # stop sending custom packets and start performing signal
        # strength measurements.
        if not self._started:
            self._send_custom_packets()
        elif self._id > 0 and time.time() >= self._scheduler_next_timestamp:
            self._scheduler_next_timestamp = self._scheduler.get_next_timestamp()
            self._send()

        time.sleep(self._loop_delay)

        # Process any data in the socket's buffer.
        try:
            data = self._connection.recv(self._buffer_size)

            # Unserialize the data (byte-encoded string).
            packet = Packet()
            packet.unserialize(data)
            self._receive(packet)
        except AttributeError:
            raise DisabledException
        except socket.error:
            return

    def _send_tx_frame(self, packet, to=None):
        """
        Send a TX frame with `packet` as payload `to` another sensor.
        """

        super(RF_Sensor_Simulator, self)._send_tx_frame(packet, to)

        self._connection.sendto(packet.serialize(), (self._ip, self._port + to))

    def _receive(self, packet):
        """
        Receive and process a `packet` from another sensor in the network.
        """

        # Show all received packets (including private ones) in simulation mode.
        self._receive_callback(packet)

        if self._id > 0:
            self._scheduler_next_timestamp = self._scheduler.synchronize(packet)

            # Create and complete the packet for the ground station.
            ground_station_packet = self._create_rssi_ground_station_packet(packet)
            ground_station_packet.set("rssi", -random.randint(30, 70))
            self._packets.append(ground_station_packet)
        elif self._buffer is not None:
            self._buffer.put(packet)
