from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View

class XBee_Device_Category(object):
    COORDINATOR = 0
    END_DEVICE = 2

class XBee_Device(object):
    def __init__(self, name, id, category):
        self.name = name
        self.id = id
        self.category = category
        self.address = "-"
        self.joined = False

class Control_Panel_Devices_View(Control_Panel_View):
    def show(self):
        """
        Show the devices view.
        """

        self._add_menu_bar()

        # Create the tree view.
        self._tree_view = QtGui.QTreeWidget()

        # Create the header for the tree view.
        header = QtGui.QTreeWidgetItem(["Device", "Property value"])
        self._tree_view.setHeaderItem(header)
        self._tree_view.header().setResizeMode(0, QtGui.QHeaderView.Stretch);

        # Fill the tree view with the devices.
        self._devices = [
            XBee_Device("Ground station", 0, XBee_Device_Category.COORDINATOR),
            XBee_Device("Vehicle 1", 1, XBee_Device_Category.END_DEVICE),
            XBee_Device("Vehicle 2", 2, XBee_Device_Category.END_DEVICE)
        ]
        self._refresh()

        # Create the refresh button.
        refresh_button = QtGui.QPushButton("Refresh")
        refresh_button.clicked.connect(lambda: self._refresh())

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(refresh_button)
        hbox.addStretch(1)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox)
        vbox.addWidget(self._tree_view)

    def _fill(self):
        """
        Fill the tree view with the device information.
        """

        categories = {
            XBee_Device_Category.COORDINATOR: "Coordinator",
            XBee_Device_Category.END_DEVICE: "End device"
        }

        # Add an entry in the tree view for each device.
        for device in self._devices:
            item = QtGui.QTreeWidgetItem(self._tree_view, [device.name])
            item_id = QtGui.QTreeWidgetItem(item, ["ID", str(device.id)])
            item_category = QtGui.QTreeWidgetItem(item, ["Category", categories[device.category]])
            item_address = QtGui.QTreeWidgetItem(item, ["Address", device.address])
            item_joined = QtGui.QTreeWidgetItem(item, ["Joined", "Yes" if device.joined else "No"])

        # Expand all items in the tree view.
        self._tree_view.expandToDepth(0)

    def _refresh(self):
        """
        Refresh the status of the ground station and the vehicles.
        """

        self._refresh_ground_station()
        self._refresh_vehicles()

    def _refresh_ground_station(self):
        """
        Refresh the status of the ground station.
        """

        identity = self._controller.xbee.get_identity()

        ground_station = self._devices[0]
        ground_station.address = identity["address"]
        ground_station.joined = identity["joined"]

        self._tree_view.clear()
        self._fill()

    def _refresh_vehicles(self):
        """
        Refresh the status of the vehicles.
        """

        self._controller.xbee.discover(self._refresh_vehicle)

    def _refresh_vehicle(self, packet):
        """
        Refresh a single vehicle using information from in
        node discovery XBee packet.
        """

        vehicle = self._devices[packet["id"]]
        vehicle.address = packet["address"]
        vehicle.joined = True

        self._tree_view.clear()
        self._fill()
