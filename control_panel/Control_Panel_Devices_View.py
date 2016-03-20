from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View

class XBee_Device_Type(object):
    COORDINATOR = 0
    END_DEVICE = 2

class XBee_Device_Name(object):
    COORDINATOR = "Coordinator"
    END_DEVICE = "End device"

class Control_Panel_Devices_View(Control_Panel_View):
    def show(self):
        """
        Show the devices view.
        """

        self._add_menu_bar()

        # Create the tree view.
        tree_view = QtGui.QTreeWidget()

        # Create the header for the tree view.
        header = QtGui.QTreeWidgetItem(["Device", "Property value"])
        tree_view.setHeaderItem(header)
        tree_view.header().setResizeMode(0, QtGui.QHeaderView.Stretch);

        # Create the items for the tree view.
        ground_station = QtGui.QTreeWidgetItem(tree_view, ["Ground station"])
        ground_station_id = QtGui.QTreeWidgetItem(ground_station, ["ID", "0"])
        ground_station_type = QtGui.QTreeWidgetItem(ground_station, ["Type", XBee_Device_Name.COORDINATOR])
        ground_station_address = QtGui.QTreeWidgetItem(ground_station, ["Address", "01:55:A2:A3:55:7E"])
        ground_station_joined = QtGui.QTreeWidgetItem(ground_station, ["Joined", "Yes"])

        # Expand all items in the tree view.
        tree_view.expandToDepth(0)

        # Create the refresh button.
        refresh_button = QtGui.QPushButton("Refresh")
        refresh_button.clicked.connect(lambda: self._refresh())

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(refresh_button)
        hbox.addStretch(1)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox)
        vbox.addWidget(tree_view)

    def _refresh(self):
        """
        Refresh the status of the ground station and the vehicles.
        """

        # TODO: update ground station status
        # TODO: update vehicle status using node discovery
        pass
