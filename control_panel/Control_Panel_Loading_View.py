import sys
from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

class Control_Panel_Loading_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Loading_View, self).__init__(controller, settings)

        self._progressBar = None
        self._label = None
        self._xbee_insertion_delay = self._settings.get("loading_xbee_insertion_delay") * 1000

    def show(self):
        """
        Show the loading view.
        """

        # Create an indeterminate progress bar.
        self._progressBar = QtGui.QProgressBar()
        self._progressBar.setRange(0, 0)

        # Create a label.
        self._label = QtGui.QLabel("Waiting for insertion of ground station XBee...")

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addStretch(1)
        vbox.addWidget(self._progressBar)
        vbox.addWidget(self._label)
        vbox.addStretch(1)

        if not isinstance(self._controller.xbee, XBee_Sensor_Simulator):
            button = QtGui.QPushButton("Switch to simulation mode")
            button.clicked.connect(self._switch)

            hbox = QtGui.QHBoxLayout()
            hbox.addStretch(1)
            hbox.addWidget(button)
            hbox.addStretch(1)

            vbox.addLayout(hbox)

        # Wait for insertion of the ground station XBee.
        QtCore.QTimer.singleShot(self._xbee_insertion_delay, self._insertion_loop)

    def _insertion_loop(self):
        """
        Execute the loop to wait for insertion of the ground station XBee.
        """

        try:
            if not isinstance(self._controller.xbee, XBee_Sensor_Simulator):
                self._controller.usb_manager.index()
                try:
                    # Assume the ground station is an XBee device.
                    self._controller.usb_manager.get_xbee_device()
                    xbee_class = "XBee_Sensor_Physical"
                except KeyError:
                    # Not an XBee device, so it must be a CC2531 device.
                    self._controller.usb_manager.get_cc2531_device()
                    xbee_class = "XBee_CC2530_Sensor_Physical"

            # Reload the sensor class.
            settings = self._controller.arguments.get_settings("control_panel")
            settings.set("controller_xbee_type", xbee_class)
            self._controller.setup_xbee()

            # An XBee has been inserted, but we need to check that it actually 
            # belongs to a ground station XBee.
            self._progressBar.setRange(0, 2)
            self._progressBar.setValue(1)
            self._label.setText("Identifying the inserted XBee...")
            self._label.repaint()
            self._controller.app.processEvents()

            self._controller.xbee.setup()
            if self._controller.xbee.id != 0:
                QtGui.QMessageBox.critical(self._controller.central_widget, "XBee error",
                                           "The inserted XBee device is not a ground station.")
                self._controller.window.close()
                sys.exit(1)

            # We now know that a valid XBee device has been inserted.
            # Therefore update the label and proceed with activating the XBee.
            self._progressBar.setValue(2)
            self._label.setText("Activating ground station XBee and wireless network...")
            self._label.repaint()
            self._controller.app.processEvents()

            self._controller.xbee.activate()
            self._controller.show_view(Control_Panel_View_Name.DEVICES)
        except KeyError:
            QtCore.QTimer.singleShot(self._xbee_insertion_delay, self._insertion_loop)

    def _switch(self):
        """
        Switch the controller XBee from physical to simulated XBees.
        """

        settings = self._controller.arguments.get_settings("control_panel")
        settings.set("controller_xbee_type", "XBee_Sensor_Simulator")
        self._controller.setup_xbee()
