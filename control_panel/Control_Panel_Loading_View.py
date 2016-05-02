import sys
from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name
from ..zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical

class Control_Panel_Loading_View(Control_Panel_View):
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

        if isinstance(self._controller.xbee, XBee_Sensor_Physical):
            button = QtGui.QPushButton("Switch to simulated XBee")
            button.clicked.connect(self._switch)

            hbox = QtGui.QHBoxLayout()
            hbox.addStretch(1)
            hbox.addWidget(button)
            hbox.addStretch(1)

            vbox.addLayout(hbox)

        # Wait for insertion of the ground station XBee.
        self._xbee_insertion_delay = self._settings.get("loading_xbee_insertion_delay") * 1000
        QtCore.QTimer.singleShot(self._xbee_insertion_delay, lambda: self._insertion_loop())

    def _insertion_loop(self):
        """
        Execute the loop to wait for insertion of the ground station XBee.
        """

        try:
            if isinstance(self._controller.xbee, XBee_Sensor_Physical):
                self._controller.usb_manager.index()
                self._controller.usb_manager.get_xbee_device()

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
            QtCore.QTimer.singleShot(self._xbee_insertion_delay, lambda: self._insertion_loop())

    def _switch(self):
        """
        Switch the controller XBee from physical to simulated XBees.
        """

        settings = self._controller.arguments.get_settings("control_panel")
        settings.set("controller_xbee_simulation", True)
        self._controller.setup_xbee()
