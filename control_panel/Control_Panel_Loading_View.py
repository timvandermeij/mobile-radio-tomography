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
        progressBar = QtGui.QProgressBar()
        progressBar.setMinimum(0)
        progressBar.setMaximum(0)

        # Create a label.
        self._label = QtGui.QLabel("Waiting for insertion of ground station XBee...")

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addStretch(1)
        vbox.addWidget(progressBar)
        vbox.addWidget(self._label)
        vbox.addStretch(1)

        # Wait for insertion of the ground station XBee.
        control_panel_settings = self._controller.arguments.get_settings("control_panel")
        self._xbee_insertion_delay = control_panel_settings.get("loading_xbee_insertion_delay") * 1000
        self._insertion_loop()

    def _insertion_loop(self):
        """
        Execute the loop to wait for insertion of the ground station XBee.
        """

        try:
            if isinstance(self._controller.xbee, XBee_Sensor_Physical):
                self._controller.usb_manager.index()
                self._controller.usb_manager.get_xbee_device()

            # We now know that a valid XBee device has been inserted.
            # Therefore update the label and proceed with activating the XBee.
            self._label.setText("Activating ground station XBee and wireless network...")
            self._label.repaint()
            self._controller.app.processEvents()

            self._controller.xbee.setup()
            if self._controller.xbee.id != 0:
                QtGui.QMessageBox.critical(self._controller.central_widget, "XBee error",
                                           "The inserted XBee device is not a ground station.")
                self._controller.window.close()
                sys.exit(1)

            self._controller.xbee.activate()
            self._controller.show_view(Control_Panel_View_Name.WAYPOINTS)
        except KeyError:
            QtCore.QTimer.singleShot(self._xbee_insertion_delay, lambda: self._insertion_loop())
