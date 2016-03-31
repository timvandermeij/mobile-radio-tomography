from functools import partial
from PyQt4 import QtGui, QtCore
from ..zigbee.XBee_Packet import XBee_Packet

class Control_Panel_XBee_Sender(object):
    """
    Handler for sending status changes to the XBee devices on the vehicles.
    """

    def __init__(self, controller, name, data, total, clear_message,
                 add_callback, done_message, ack_message, max_retries,
                 retry_interval):
        self._controller = controller
        self._name = name

        self._clear_message = clear_message
        self._add_callback = add_callback
        self._done_message = done_message
        self._ack_message = ack_message

        self._max_retries = max_retries
        self._retry_interval = retry_interval

        self._labels = dict([(vehicle, "") for vehicle in data])

        self._retry_counts = dict([(vehicle, self._max_retries) for vehicle in data])
        self._indexes = dict([(vehicle, -1) for vehicle in data])

        self._timers = {}

        self._data = data
        self._total = total

    def start(self):
        self._controller.add_packet_callback(self._ack_message,
                                             self._receive_ack)

        # Create a progress dialog and send the data to the vehicles.
        self._progress = QtGui.QProgressDialog(self._controller.central_widget)
        self._progress.setMinimum(0)
        self._progress.setMaximum(self._total)
        self._progress.setWindowModality(QtCore.Qt.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.setCancelButtonText("Cancel")
        self._progress.canceled.connect(lambda: self._cancel())
        self._progress.setWindowTitle("Sending {}s".format(self._name))
        self._progress.setLabelText("Initializing...")
        self._progress.open()

        for vehicle in self._data:
            timer = QtCore.QTimer()
            timer.setInterval(self._retry_interval * 1000)
            timer.setSingleShot(True)
            # Bind timeout signal to retry for the current vehicle.
            timer.timeout.connect(partial(self._retry, vehicle))
            self._timers[vehicle] = timer

        for vehicle in self._data:
            self._send_clear(vehicle)

    def _send_clear(self, vehicle):
        packet = XBee_Packet()
        packet.set("specification", self._clear_message)
        packet.set("to_id", vehicle)

        self._controller.xbee.enqueue(packet, to=vehicle)

        self._set_label(vehicle, "Clearing old {}s".format(self._name))
        self._timers[vehicle].start()

    def _send_one(self, vehicle):
        index = self._indexes[vehicle]
        if len(self._data[vehicle]) <= index:
            # Enqueue a packet indicating that sending data to this vehicle is 
            # done.
            packet = XBee_Packet()
            packet.set("specification", self._done_message)
            packet.set("to_id", vehicle)
            self._controller.xbee.enqueue(packet, to=vehicle)

            self._update_value()
            return

        data = self._data[vehicle][index]

        packet = self._add_callback(vehicle, index, data)

        self._controller.xbee.enqueue(packet, to=vehicle)

        self._set_label(vehicle, "Sending {} #{}: {}".format(self._name, index, data))
        self._timers[vehicle].start()

    def _receive_ack(self, packet):
        vehicle = packet.get("sensor_id")
        index = packet.get("next_index")

        if vehicle not in self._timers:
            return

        self._indexes[vehicle] = index
        self._retry_counts[vehicle] = self._max_retries + 1

    def _retry(self, vehicle):
        self._retry_counts[vehicle] -= 1
        if self._retry_counts[vehicle] > 0:
            if self._indexes[vehicle] == -1:
                self._send_clear(vehicle)
            else:
                self._send_one(vehicle)
        else:
            self._cancel("Vehicle {}: Maximum retry attempts for {} reached".format(vehicle, "clearing {}s".format(self._name) if self._indexes[vehicle] == -1 else "{} #{}".format(self._name, self._indexes[vehicle])))

    def _set_label(self, vehicle, text):
        self._labels[vehicle] = text
        self._update_labels()
        self._update_value()

    def _update_labels(self):
        labels = []
        for vehicle in sorted(self._labels.iterkeys()):
            label = self._labels[vehicle]
            if self._retry_counts[vehicle] < self._max_retries:
                retry = " ({} attempts remaining)".format(self._retry_counts[vehicle])
            else:
                retry = ""

            labels.append("Vehicle {}: {}{}".format(vehicle, label, retry))

        self._progress.setLabelText("\n".join(labels))

    def _update_value(self):
        self._progress.setValue(max(0, min(self._total, sum(self._indexes.values()))))

    def _cancel(self, message=None):
        self._controller.remove_packet_callback(self._ack_message)

        for timer in self._timers.values():
            timer.stop()

        if self._progress is not None:
            self._progress.cancel()
            self._progress.deleteLater()

        if message is not None:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Sending failed", message)
