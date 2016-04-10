import json
import os
from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View
from Control_Panel_Widgets import WaypointsTableWidget
from Control_Panel_XBee_Sender import Control_Panel_XBee_Sender
from ..zigbee.XBee_Packet import XBee_Packet

class Control_Panel_Waypoints_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Waypoints_View, self).__init__(controller, settings)

        self._max_retries = self._settings.get("waypoints_max_retries")
        self._retry_interval = self._settings.get("waypoints_retry_interval")

    def load(self, data):
        self._listWidget = QtGui.QListWidget()
        self._stackedLayout = QtGui.QStackedLayout()

        self._vehicle_labels = []
        self._tables = []
        self._column_labels = ["north", "east", "altitude", "wait for vehicle"]
        # Default values that are used when exporting/importing tables.
        # We initially require data for the north/east column, but the altitude 
        # and wait ID can be left out.
        self._column_defaults = (None, None, 0, False)

        for vehicle in xrange(1, self._controller.xbee.number_of_sensors + 1):
            # Create the list item for the vehicle.
            self._listWidget.addItem("Waypoints for vehicle {}".format(vehicle))

            # Create the table for the vehicle.
            table = WaypointsTableWidget(self._column_labels)

            self._tables.append(table)
            self._stackedLayout.addWidget(table)

        if "waypoints" in data:
            self._import_waypoints(data["waypoints"], from_json=False)

    def save(self):
        try:
            return {
                "waypoints": self._export_waypoints(repeat=False)[0]
            }
        except ValueError as e:
            return {}

    def show(self):
        """
        Show the waypoints view.
        """

        self._add_menu_bar()

        self._listWidget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        self._listWidget.setCurrentRow(0)
        self._listWidget.currentRowChanged.connect(self._stackedLayout.setCurrentIndex)

        # Create the buttons for adding new rows and sending the waypoints.
        add_row_button = QtGui.QPushButton("Add row")
        add_row_button.clicked.connect(self._add_row)
        import_button = QtGui.QPushButton("Import")
        import_button.clicked.connect(self._import)
        export_button = QtGui.QPushButton("Export")
        export_button.clicked.connect(self._export)
        send_button = QtGui.QPushButton("Send")
        send_button.clicked.connect(self._send)

        # Create the layout and add the widgets.
        hbox_stacks = QtGui.QHBoxLayout()
        hbox_stacks.addWidget(self._listWidget)
        hbox_stacks.addLayout(self._stackedLayout)

        hbox_buttons = QtGui.QHBoxLayout()
        hbox_buttons.addWidget(add_row_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(import_button)
        hbox_buttons.addWidget(export_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(send_button)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox_stacks)
        vbox.addLayout(hbox_buttons)

    def _add_row(self):
        """
        Add a row to all tables at the same time.
        """

        for table in self._tables:
            table.insertRow(table.rowCount())

    def _export_waypoints(self, repeat=True):
        """
        Create a list of waypoints (tuples) per vehicle.
        """

        waypoints = {}
        total = 0
        for index, table in enumerate(self._tables):
            # Keep vehicle index as string here since send and save make use of 
            # integer indices, while JSON export will automatically convert 
            # them to string keys.
            vehicle = index + 1
            previous = self._column_defaults
            for row in range(table.rowCount()):
                data = []
                for col in range(len(self._column_labels)):
                    item = table.item(row, col)
                    # Handle unchanged columns (no item widget) or empty 
                    # columns (text contents equals to empty string)
                    if item is None or item.text() == "":
                        data.append(None)
                    else:
                        data.append(item.text())

                if all(item is None for item in data) and not previous:
                    # If the first table row is completely empty, then silently 
                    # ignore this row.
                    continue

                if any(item is None and prev is None for item, prev in zip(data, previous)):
                    # If a column has no data and no previous data either, then 
                    # we have missing information.
                    raise ValueError("Missing coordinates for vehicle {}, row {} and no previous waypoint".format(vehicle, row))

                for i, col in enumerate(self._column_labels):
                    if data[i] is None:
                        # If a table cell is empty, use the previous waypoint's 
                        # coordinates for the current waypoint.
                        data[i] = previous[i] if repeat else None
                    else:
                        try:
                            data[i] = int(data[i])
                        except ValueError:
                            raise ValueError("Invalid integer for vehicle {}, row {}, column {}: {}".format(vehicle, row, col, data[i]))

                if vehicle not in waypoints:
                    waypoints[vehicle] = [tuple(data)]
                else:
                    waypoints[vehicle].append(tuple(data))

                total += 1
                previous = tuple(data)

        return waypoints, total

    def _import_waypoints(self, waypoints, from_json=True):
        for index, table in enumerate(self._tables):
            # Allow either string or numeric indices depending on import source
            vehicle = str(index + 1) if from_json else index + 1
            if vehicle not in waypoints:
                continue

            table.removeRows()
            for row, waypoint in enumerate(waypoints[vehicle]):
                table.insertRow(row)
                for col in range(len(self._column_labels)):
                    if col >= len(waypoint):
                        if self._column_defaults[col] is None:
                            # Data is required for this column, but it is not 
                            # provided.
                            raise ValueError("Row #{} has missing information for column '{}'".format(row + 1, self._column_labels[col]))

                        break

                    if waypoint[col] != self._column_defaults[col]:
                        item = str(waypoint[col])
                        table.setItem(row, col, QtGui.QTableWidgetItem(item))

    def _import(self):
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

        try:
            self._import_waypoints(waypoints)
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Waypoint incorrect", e.message)

    def _export(self):
        try:
            waypoints, total = self._export_waypoints()
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

    def _send(self):
        """
        Send the waypoints from all tables to the corresponding vehicles.
        """

        try:
            waypoints, total = self._export_waypoints()
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Waypoint incorrect", e.message)
            return

        if total == 0:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "No waypoints",
                                       "There are no vehicles with waypoints.")
            return

        configuration = {
            "name": "waypoint",
            "clear_message": "waypoint_clear",
            "add_callback": self._make_add_waypoint_packet,
            "done_message": "waypoint_done",
            "ack_message": "waypoint_ack",
            "max_retries": self._max_retries,
            "retry_interval": self._retry_interval
        }
        sender = Control_Panel_XBee_Sender(self._controller, waypoints, total,
                                           configuration)
        sender.start()

    def _make_add_waypoint_packet(self, vehicle, index, waypoint):
        packet = XBee_Packet()
        packet.set("specification", "waypoint_add")
        packet.set("latitude", waypoint[0])
        packet.set("longitude", waypoint[1])
        packet.set("index", index)
        packet.set("to_id", vehicle)

        return packet
