import json
import os
from functools import partial
from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View
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
        self._column_labels = ["x", "y"]

        for vehicle in xrange(1, self._controller.xbee.number_of_sensors + 1):
            # Create the list item for the vehicle.
            self._listWidget.addItem("Waypoints for vehicle {}".format(vehicle))

            # Create the table for the vehicle.
            table = QtGui.QTableWidget()
            table.setRowCount(1)
            table.setColumnCount(len(self._column_labels))
            table.setHorizontalHeaderLabels(self._column_labels)
            horizontalHeader = table.horizontalHeader()
            for i in range(len(self._column_labels)):
                horizontalHeader.setResizeMode(i, QtGui.QHeaderView.Stretch)

            # Create the context menu for the rows in the table.
            table.verticalHeader().setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            remove_rows_action = QtGui.QAction("Remove row(s)", table)
            remove_rows_action.triggered.connect(partial(self._remove_rows, table))
            table.verticalHeader().addAction(remove_rows_action)

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

    def _remove_rows(self, table):
        """
        Remove one or more selected rows from a table.
        """

        items = table.selectionModel().selectedRows()
        rows = [item.row() for item in items]
        for row in reversed(sorted(rows)):
            table.removeRow(row)

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
            previous = ()
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

                if any(item is None for item in data) and not previous:
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

            for row in range(table.rowCount()):
                table.removeRow(row)
            for row, waypoint in enumerate(waypoints[vehicle]):
                table.insertRow(row)
                for col in range(len(self._column_labels)):
                    if waypoint[col] is not None:
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

        self._import_waypoints(waypoints)

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
