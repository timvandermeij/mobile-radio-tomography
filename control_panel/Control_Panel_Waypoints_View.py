import json
import os
from functools import partial
from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View
from ..zigbee.XBee_Packet import XBee_Packet

class Control_Panel_Waypoints_View(Control_Panel_View):
    def __init__(self, controller):
        super(Control_Panel_Waypoints_View, self).__init__(controller)

        settings = self._controller.arguments.get_settings("control_panel")
        self._max_retries = settings.get("waypoints_max_retries")
        self._retry_interval = settings.get("waypoints_retry_interval")
        self._clear_send()

    def clear(self, layout=None):
        super(Control_Panel_Waypoints_View, self).clear(layout)

        self._controller.remove_packet_callback("waypoint_ack")

    def show(self):
        """
        Show the waypoints view.
        """

        self._add_menu_bar()
        self._controller.add_packet_callback("waypoint_ack", self._receive_ack)

        labels = []
        tables = []

        for vehicle in [1, 2]:
            # Create the label for the vehicle.
            label = QtGui.QLabel("Waypoints for vehicle {}:".format(vehicle))
            labels.append(label)

            # Create the table for the vehicle.
            table = QtGui.QTableWidget()
            table.setRowCount(1)
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["x", "y"])
            table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
            table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
            tables.append(table)

            # Create the context menu for the rows in the table.
            table.verticalHeader().setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            remove_rows_action = QtGui.QAction("Remove row(s)", table)
            remove_rows_action.triggered.connect(partial(self._remove_rows, table))
            table.verticalHeader().addAction(remove_rows_action)

        # Create the buttons for adding new rows and sending the waypoints.
        add_row_button = QtGui.QPushButton("Add row")
        add_row_button.clicked.connect(lambda: self._add_row(tables))
        import_button = QtGui.QPushButton("Import")
        import_button.clicked.connect(lambda: self._import(tables))
        export_button = QtGui.QPushButton("Export")
        export_button.clicked.connect(lambda: self._export(tables))
        send_button = QtGui.QPushButton("Send")
        send_button.clicked.connect(lambda: self._send(tables))

        # Create the layout and add the widgets.
        hbox_labels = QtGui.QHBoxLayout()
        for label in labels:
            hbox_labels.addWidget(label)

        hbox_tables = QtGui.QHBoxLayout()
        for table in tables:
            hbox_tables.addWidget(table)

        hbox_buttons = QtGui.QHBoxLayout()
        hbox_buttons.addWidget(add_row_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(import_button)
        hbox_buttons.addWidget(export_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(send_button)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox_labels)
        vbox.addLayout(hbox_tables)
        vbox.addLayout(hbox_buttons)

    def _add_row(self, tables):
        """
        Add a row to all tables at the same time.
        """

        for table in tables:
            table.insertRow(table.rowCount())

    def _remove_rows(self, table):
        """
        Remove one or more selected rows from a table.
        """

        items = table.selectionModel().selectedRows()
        rows = [item.row() for item in items]
        for row in reversed(sorted(rows)):
            table.removeRow(row)

    def _make_waypoints(self, tables):
        """
        Create a list of waypoints (tuples) per vehicle.
        """

        waypoints = {}
        total = 0
        for index, table in enumerate(tables):
            vehicle = index + 1
            previous = ()
            for row in range(table.rowCount()):
                x = table.item(row, 0)
                y = table.item(row, 1)
                if (x is None or y is None) and not previous:
                    raise ValueError("Missing coordinates for vehicle {}, row {} and no previous waypoint".format(vehicle, row))

                if x is None:
                    # If a table cell is empty, use the previous waypoint's 
                    # coordinates for the current waypoint.
                    x = previous[0]
                else:
                    try:
                        x = int(x.text())
                    except ValueError:
                        raise ValueError("Invalid integer for vehicle {}, row {}, column x: {}".format(vehicle, row, x.text()))

                if y is None:
                    y = previous[1]
                else:
                    try:
                        y = int(y.text())
                    except ValueError:
                        raise ValueError("Invalid integer for vehicle {}, row {}, column y: {}".format(vehicle, row, y.text()))

                if vehicle not in waypoints:
                    waypoints[vehicle] = [(x, y)]
                else:
                    waypoints[vehicle].append((x, y))

                total += 1
                previous = (x, y)

        return waypoints, total

    def _import(self, tables):
        fn = QtGui.QFileDialog.getOpenFileName(self._controller.central_widget,
                                               "Import file", os.getcwd(),
                                               "JSON files (*.json)")
        if fn == "":
            return

        try:
            with open(fn, 'r') as import_file:
                waypoints = json.load(import_file)
                if isinstance(waypoints, list):
                    try:
                        waypoints = {
                            1: [sensor_pairs[0] for sensor_pairs in waypoints],
                            2: [sensor_pairs[1] for sensor_pairs in waypoints]
                        }
                    except IndexError:
                        raise ValueError("JSON list must contain sensor pairs")
                elif not isinstance(waypoints, dict):
                    raise ValueError("Waypoints must be a JSON list or array")
        except IOError as e:
            message = "Could not open file '{}': {}".format(fn, e.strerror)
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "File error", message)
            return
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "JSON error", e.message)
            return

        for index, table in enumerate(tables):
            vehicle = str(index + 1)
            for row in range(table.rowCount()):
                table.removeRow(row)
            for row, waypoint in enumerate(waypoints[vehicle]):
                table.insertRow(row)
                table.setItem(row, 0, QtGui.QTableWidgetItem(str(waypoint[0])))
                table.setItem(row, 1, QtGui.QTableWidgetItem(str(waypoint[1])))

    def _export(self, tables):
        try:
            waypoints, total = self._make_waypoints(tables)
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Waypoint incorrect", e.message)
            return

        fn = QtGui.QFileDialog.getSaveFileName(self._controller.central_widget,
                                               "Export file", os.getcwd(),
                                               "JSON files (*.json)")
        if fn == "":
            return

        try:
            with open(fn, 'w') as export_file:
                json.dump(waypoints, export_file)
        except IOError as e:
            message = "Could not open file '{}': {}".format(fn, e.strerror)
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "File error", message)

    def _send(self, tables):
        """
        Send the waypoints from all tables to the corresponding vehicles.
        """

        try:
            waypoints, total = self._make_waypoints(tables)
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Waypoint incorrect", e.message)
            return

        # Create a progress dialog and send the waypoints to the vehicles.
        self._progress = QtGui.QProgressDialog(self._controller.central_widget)
        self._progress.setMinimum(0)
        self._progress.setMaximum(total)
        self._progress.setWindowModality(QtCore.Qt.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.setCancelButtonText("Cancel")
        self._progress.canceled.connect(lambda: self._cancel())
        self._progress.setWindowTitle("Sending waypoints")
        self._progress.setLabelText("Initializing...")
        self._progress.open()

        self._labels = dict([(vehicle, "") for vehicle in waypoints])

        self._retry_counts = dict([(vehicle, self._max_retries) for vehicle in waypoints])
        self._indexes = dict([(vehicle, -1) for vehicle in waypoints])

        self._timers = {}
        for vehicle in waypoints:
            timer = QtCore.QTimer()
            timer.setInterval(self._retry_interval)
            timer.setSingleShot(True)
            # Bind timeout signal to retry for the current vehicle.
            timer.timeout.connect(partial(self._retry, vehicle))
            self._timers[vehicle] = timer

        self._waypoints = waypoints
        self._total = total
        for vehicle in self._waypoints:
            self._send_clear(vehicle)

    def _send_clear(self, vehicle):
        packet = XBee_Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", vehicle)

        self._controller.xbee.enqueue(packet, to=vehicle)

        self._set_label(vehicle, "Clearing old waypoints")
        self._timers[vehicle].start()

    def _send_one(self, vehicle):
        index = self._indexes[vehicle]
        if len(self._waypoints[vehicle]) <= index:
            # Enqueue a packet indicating that waypoint sending
            # for this vehicle is done.
            packet = XBee_Packet()
            packet.set("specification", "waypoint_done")
            packet.set("to_id", vehicle)
            self._controller.xbee.enqueue(packet, to=vehicle)

            self._update_value()
            return

        waypoint = self._waypoints[vehicle][index]

        packet = XBee_Packet()
        packet.set("specification", "waypoint_add")
        packet.set("latitude", waypoint[0])
        packet.set("longitude", waypoint[1])
        packet.set("index", index)
        packet.set("to_id", vehicle)

        self._controller.xbee.enqueue(packet, to=vehicle)

        self._set_label(vehicle, "Sending waypoint #{} ({}, {})".format(index, waypoint[0], waypoint[1]))
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
            self._cancel("Vehicle {}: Maximum retry attempts for {} reached".format(vehicle, "clearing waypoints" if self._indexes[vehicle] == -1 else "index {}".format(self._indexes[vehicle])))

    def _set_label(self, vehicle, text):
        self._labels[vehicle] = text
        self._update_labels()
        self._update_value()

    def _update_labels(self):
        self._progress.setLabelText("\n".join("Vehicle {}: {}{}".format(vehicle, label, " ({} attempts remaining)".format(self._retry_counts[vehicle]) if self._retry_counts[vehicle] < self._max_retries else "") for vehicle, label in self._labels.iteritems()))

    def _update_value(self):
        self._progress.setValue(max(0, min(self._total, sum(self._indexes.values()))))

    def _cancel(self, message=None):
        for timer in self._timers.values():
            timer.stop()

        if self._progress is not None:
            self._progress.cancel()
            self._progress.deleteLater()

        if message is not None:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Sending failed", message)

        self._clear_send()

    def _clear_send(self):
        # Clear variables used in the _send method and its submethods
        self._progress = None
        self._labels = {}
        self._retry_counts = {}
        self._indexes = {}
        self._waypoints = {}
        self._total = 0
        self._timers = {}
