from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name

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
        label = QtGui.QLabel("Waiting for insertion of ground station XBee...")

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addStretch(1)
        vbox.addWidget(progressBar)
        vbox.addWidget(label)
        vbox.addStretch(1)

        # Wait for insertion of the ground station XBee.
        self._insertion_loop()

    def _insertion_loop(self):
        """
        Execute the loop to wait for insertion of the ground station XBee.
        """

        try:
            self._controller.usb_manager.index()
            self._controller.usb_manager.get_xbee_device()
            self._controller.switch_view(Control_Panel_View_Name.RECONSTRUCTION)
        except KeyError:
            control_panel_settings = self._controller.arguments.get_settings("control_panel")
            xbee_insertion_delay = control_panel_settings.get("xbee_insertion_delay") * 1000
            QtCore.QTimer.singleShot(xbee_insertion_delay, self._insertion_loop)
