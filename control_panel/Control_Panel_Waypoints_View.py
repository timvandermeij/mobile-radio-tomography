from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View

class Control_Panel_Waypoints_View(Control_Panel_View):
    def show(self):
        """
        Show the waypoints view.
        """

        # Create the label for the first vehicle.
        label_1 = QtGui.QLabel("Waypoints for vehicle 1:")

        # Create the table for the first vehicle.
        table_1 = QtGui.QTableWidget()
        table_1.setRowCount(16)
        table_1.setColumnCount(2)
        table_1.setHorizontalHeaderLabels(["x", "y"])
        table_1.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        table_1.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)

        # Create the label for the first vehicle.
        label_2 = QtGui.QLabel("Waypoints for vehicle 2:")

        # Create the table for the second vehicle.
        table_2 = QtGui.QTableWidget()
        table_2.setRowCount(16)
        table_2.setColumnCount(2)
        table_2.setHorizontalHeaderLabels(["x", "y"])
        table_2.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        table_2.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)

        tables = [table_1, table_2]

        # Create the buttons for adding new rows and sending the waypoints.
        add_row_button = QtGui.QPushButton("Add row")
        add_row_button.clicked.connect(lambda: self._add_row(tables))
        send_button = QtGui.QPushButton("Send")
        send_button.clicked.connect(lambda: self._send(tables))

        # Create the layout and add the widgets.
        hbox_labels = QtGui.QHBoxLayout()
        hbox_labels.addWidget(label_1)
        hbox_labels.addWidget(label_2)

        hbox_tables = QtGui.QHBoxLayout()
        hbox_tables.addWidget(table_1)
        hbox_tables.addWidget(table_2)

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

    def _send(self, tables):
        """
        Send the waypoints from all tables to the corresponding vehicles.
        """

        waypoints = {}

        for index, table in enumerate(tables):
            vehicle = index + 1
            for row in range(table.rowCount()):
                x = table.item(row, 0)
                y = table.item(row, 1)
                if x is not None and y is not None:
                    x = int(x.text())
                    y = int(y.text())
                    if vehicle not in waypoints:
                        waypoints[vehicle] = [(x, y)]
                    else:
                        waypoints[vehicle].append((x, y))

        # TODO: send waypoints to vehicles using XBee
