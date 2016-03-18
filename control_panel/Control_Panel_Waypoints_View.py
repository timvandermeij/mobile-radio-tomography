import time
from functools import partial
from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View

class Control_Panel_Waypoints_View(Control_Panel_View):
    def show(self):
        """
        Show the waypoints view.
        """

        self._add_menu_bar()

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

            # Create the context menu for the rows in the table. We use
            # `functools.partial` because Python only creates new bindings in
            # namespaces through assignment and parameter lists of functions.
            # The parameter `table` is therefore not defined in the namespace of
            # the lambda, but rather in the namespace of `show()`.
            table.verticalHeader().setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            remove_rows_action = QtGui.QAction("Remove row(s)", table)
            remove_rows_action.triggered.connect(partial(self._remove_rows, table))
            table.verticalHeader().addAction(remove_rows_action)

        # Create the buttons for adding new rows and sending the waypoints.
        add_row_button = QtGui.QPushButton("Add row")
        add_row_button.clicked.connect(lambda: self._add_row(tables))
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
        # Create a list of waypoints (tuples) per vehicle.
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
                    # If a table cell is empty, use the previous waypoints's 
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

                previous = (x, y)

        return waypoints, total

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
        progress = QtGui.QProgressDialog(self._controller.central_widget)
        progress.setMinimum(0)
        progress.setMaximum(total)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)

        count = 0
        for vehicle in waypoints:
            for waypoint in waypoints[vehicle]:
                progress.setLabelText("Sending waypoint ({}, {}) to vehicle {}...".format(waypoint[0], waypoint[1], vehicle))
                progress.setValue(count)
                # TODO: send waypoint to the vehicle using the XBee device and remove `time.sleep`
                count += 1
                time.sleep(0.1)

        progress.setValue(total)
        progress.deleteLater()
