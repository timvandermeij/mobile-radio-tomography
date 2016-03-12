# TODO: replace XBee device identity in the settings file

import sys
import time
import usb
from PyQt4 import QtCore, QtGui

class Dashboard(QtGui.QWidget):
    def __init__(self, settings):
        """
        Initialize the dashboard window.
        """

        super(Dashboard, self).__init__()
        self.settings = settings

        # Set the dimensions, title and icon of the window.
        self.setGeometry(0, 0, 800, 600)
        self.setWindowTitle("Mobile radio tomography")
        self.setWindowIcon(QtGui.QIcon("assets/mobile-radio-tomography.png"))

        # Center the window.
        resolution = QtGui.QDesktopWidget().screenGeometry()
        frame_size = self.frameSize()
        self.move(resolution.width() / 2 - frame_size.width() / 2,
                  resolution.height() / 2 - frame_size.height() / 2)

        # Show the loading view.
        self._loading()

    def _loading(self):
        """
        Create the loading view.
        """

        # Create an indeterminate progress bar.
        progressBar = QtGui.QProgressBar(self)
        progressBar.setMinimum(0)
        progressBar.setMaximum(0)

        # Create a label.
        label = QtGui.QLabel("Waiting for insertion of ground station XBee...", self)

        # Create a vertical box layout and add the progress bar and label.
        vbox = QtGui.QVBoxLayout(self)
        vbox.addStretch(1)
        vbox.addWidget(progressBar)
        vbox.addWidget(label)
        vbox.addStretch(1)

        # Wait for insertion of the ground station XBee.
        self._loading_loop()

    def _loading_loop(self):
        """
        Execute the loading loop to wait for insertion of
        the ground station XBee.
        """

        xbee_insertion_delay = self.settings.get("xbee_insertion_delay")
        xbee_found = False

        try:
            xbee_identity = self.settings.get("xbee_identity")
            xbee_identity = [str(value) for value in xbee_identity]
            for device in usb.core.find(find_all=True):
                device_identity = [hex(device.idVendor), hex(device.idProduct)]
                if device_identity == xbee_identity:
                    xbee_found = True
        finally:
            if not xbee_found:
                QtCore.QTimer.singleShot(xbee_insertion_delay, self._loading_loop)
            else:
                self._control()

    def _control(self):
        """
        Create the control view.
        """

        print("Reached the control view!")
        sys.exit()
