from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name

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

        # Create the buttons for adding new rows and sending the waypoints.
        add_row_button = QtGui.QPushButton("Add row")
        add_row_button.clicked.connect(lambda: self._add_row(table_1, table_2))
        send_button = QtGui.QPushButton("Send")

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

    def _add_row(self, table_1, table_2):
        """
        Add a row to both tables at the same time.
        """

        table_1.insertRow(table_1.rowCount())
        table_2.insertRow(table_2.rowCount())
