# Core imports
import random
import struct
import time

# Library import
from xbee import ZigBee

# Package imports
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor_Physical import RF_Sensor_Physical

class RF_Sensor_Physical_XBee(RF_Sensor_Physical):
    """
    Physical RF sensor for the XBee branded hardware.
    """

    def __init__(self, arguments, thread_manager, location_callback,
                 receive_callback, valid_callback, usb_manager=None):
        """
        Initialize the physical RF sensor for XBee branded hardware.
        """

        super(RF_Sensor_Physical_XBee, self).__init__(arguments, thread_manager,
                                                      location_callback,
                                                      receive_callback,
                                                      valid_callback,
                                                      usb_manager=usb_manager)

        self._packets = {}

        self._sensor = None
        self._port = self._settings.get("port")
        self._node_identifier_set = False
        self._address_set = False
        self._response_delay = self._settings.get("response_delay")
        self._startup_delay = self._settings.get("startup_delay")

        self._sensors = self._settings.get("sensors")
        for index, address in enumerate(self._sensors):
            self._sensors[index] = address.decode("string_escape")

    @property
    def type(self):
        """
        Get the type of the RF sensor.

        The type is equal to the name of the settings group.
        """

        return "rf_sensor_physical_xbee"

    def activate(self):
        """
        Activate the sensor to start sending and receiving packets.
        """

        # We need this because we only want the last part of this method
        # to be executed when the sensor originally was not activated.
        originally_activated = self._activated

        super(RF_Sensor_Physical_XBee, self).activate()

        if not originally_activated:
            while not self._joined:
                self._sensor.send("at", command="AI")
                time.sleep(self._response_delay)

            self._synchronize()

    def deactivate(self):
        """
        Deactivate the sensor to stop sending and receiving packets.
        """

        if self._connection is not None:
            # Halt the internal XBee library thread to ensure that this 
            # unregistered thread is also stopped. Only do so when the thread
            # is still alive. For example, in tests the connection may be
            # started, but not the thread. In that case the `halt` method may
            # raise an exception about joining a thread before it is started.
            if self._sensor.is_alive():
                self._sensor.halt()

        super(RF_Sensor_Physical_XBee, self).deactivate()

    def discover(self, callback):
        """
        Discover all RF sensors in the network. The `callback` function is
        called when an RF sensor reports its identity.
        """

        super(RF_Sensor_Physical_XBee, self).discover(callback)

        self._sensor.send("at", command="ND")

    def _setup(self):
        """
        Setup the RF sensor by opening the connection to it.
        """

        if self._port:
            self._connection = self._usb_manager.get_xbee_device(self._port)
        else:
            self._connection = self._usb_manager.get_xbee_device()

        self._sensor = ZigBee(self._connection, callback=self._receive,
                              error_callback=self._error)

        time.sleep(self._startup_delay)

        # Identify the sensor by fetching its node identifier and address.
        while not self._node_identifier_set:
            self._sensor.send("at", command="NI")
            time.sleep(self._response_delay)

        while not self._address_set:
            self._sensor.send("at", command="SH")
            time.sleep(self._response_delay)
            self._sensor.send("at", command="SL")
            time.sleep(self._response_delay)

    def _error(self, *args):
        """
        Handle an exception within the XBee sensor thread.
        """

        super(RF_Sensor_Physical_XBee, self).interrupt()

    def _loop_body(self):
        """
        Body of the sensor loop.

        This is extracted into a separate method to make testing easier, as well
        as for keeping the `_loop` implementation in the base class.
        """

        # Ensure that the sensor has joined the network.
        if not self._joined:
            time.sleep(self._loop_delay)
            return

        super(RF_Sensor_Physical_XBee, self)._loop_body()

    def _send(self):
        """
        Send a broadcast packet to each other sensor in the network and
        send collected packets to the ground station.
        """

        # Create and send the RSSI broadcast packets.
        packet = self._create_rssi_broadcast_packet()
        for to_id in xrange(1, self._number_of_sensors + 1):
            if to_id == self._id:
                continue

            self._send_tx_frame(packet, to_id)

        # Send collected packets to the ground station.
        for frame_id in self._packets.keys():
            packet = self._packets[frame_id]
            if packet.get("rssi") is None:
                continue

            self._send_tx_frame(packet, 0)
            self._packets.pop(frame_id)

    def _send_tx_frame(self, packet, to=None):
        """
        Send a TX frame with `packet` as payload `to` another sensor.
        """

        super(RF_Sensor_Physical_XBee, self)._send_tx_frame(packet, to)

        self._sensor.send("tx", dest_addr_long=self._sensors[to], dest_addr="\xFF\xFE",
                          frame_id="\x00", data=packet.serialize())

    def _receive(self, packet=None):
        """
        Receive and process a `packet` from another sensor in the network.
        """

        if packet is None:
            raise TypeError("Packet must be provided")

        if packet["id"] == "rx":
            self._process(packet)
        elif packet["id"] == "at_response":
            self._process_at_response(packet)

    def _process(self, packet, **kwargs):
        """
        Process a `Packet` object `packet`.
        """

        # Convert the RX packet to a `Packet` object according to specifications.
        rx_packet = Packet()
        rx_packet.unserialize(packet["rf_data"])

        super(RF_Sensor_Physical_XBee, self)._process(rx_packet)

        self._process_rssi_broadcast_packet(rx_packet)

    def _process_rssi_broadcast_packet(self, packet):
        """
        Helper method for processing a `Packet` object `packet` that has been
        created according to the "rssi_broadcast" specification.
        """

        # Synchronize the scheduler using the timestamp in the packet.
        self._scheduler_next_timestamp = self._scheduler.synchronize(packet)

        # Create the packet for the ground station.
        ground_station_packet = self._create_rssi_ground_station_packet(packet)

        # Generate a frame ID to be able to match this packet and the
        # associated RSSI (DB command) request.
        frame_id = chr(random.randint(1, 255))
        self._packets[frame_id] = ground_station_packet

        # Request the RSSI value for the received packet.
        self._sensor.send("at", command="DB", frame_id=frame_id)

    def _process_at_response(self, at_packet):
        """
        Helper method for processing an XBee `at_packet`.
        """

        if at_packet["command"] == "DB":
            # RSSI value has been received. Update the original packet.
            if at_packet["frame_id"] in self._packets:
                original_packet = self._packets[at_packet["frame_id"]]
                original_packet.set("rssi", -ord(at_packet["parameter"]))
        elif at_packet["command"] == "SH":
            # Serial number (high) has been received.
            if self._address is None:
                self._address = at_packet["parameter"]
            elif at_packet["parameter"] not in self._address:
                self._address = at_packet["parameter"] + self._address
                self._address_set = True
        elif at_packet["command"] == "SL":
            # Serial number (low) has been received.
            if self._address is None:
                self._address = at_packet["parameter"]
            elif at_packet["parameter"] not in self._address:
                self._address = self._address + at_packet["parameter"]
                self._address_set = True
        elif at_packet["command"] == "NI":
            # Node identifier has been received.
            self._id = int(at_packet["parameter"])
            self._scheduler.id = self._id
            self._node_identifier_set = True
        elif at_packet["command"] == "AI":
            # Association indicator has been received.
            if at_packet["parameter"] == "\x00":
                self._joined = True
        elif at_packet["command"] == "ND":
            # Node discovery packet has been received.
            packet = at_packet["parameter"]
            self._discovery_callback({
                "id": int(packet["node_identifier"]),
                "address": self._format_address(packet["source_addr_long"])
            })

    def _format_address(self, address):
        """
        Format a given `address` for pretty printing.
        """

        if address is None:
            return "-"

        address = "%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x" % struct.unpack("BBBBBBBB", address)
        return address.upper()
