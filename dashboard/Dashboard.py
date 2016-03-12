# TODO: replace XBee device identity in the settings file
# TODO: replace random image with actual reconstruction

import numpy as np
import sys
import time
import usb
from PyQt4 import QtCore, QtGui

class Dashboard(QtGui.QMainWindow):
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

        # Set the central widget.
        self._central_widget = QtGui.QWidget()
        self.setCentralWidget(self._central_widget)

        # Show the loading view.
        self._loading()

    def _reset(self):
        """
        Reset the current layout of the window, thereby deleting any
        existing widgets.
        """

        layout = self._central_widget.layout()

        # Delete all widgets in the layout.
        if layout is not None:
            for item in reversed(range(layout.count())):
                widget = layout.itemAt(item).widget()
                if widget is not None:
                    widget.setParent(None)

        # Delete the layout itself.
        QtCore.QObjectCleanupHandler().add(layout)

    def _loading(self):
        """
        Create the loading view.
        """

        self._reset()

        # Create an indeterminate progress bar.
        progressBar = QtGui.QProgressBar(self)
        progressBar.setMinimum(0)
        progressBar.setMaximum(0)

        # Create a label.
        label = QtGui.QLabel("Waiting for insertion of ground station XBee...", self)

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout(self._central_widget)
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

        self._reset()

        # Create the menu bar.
        startAction = QtGui.QAction("Start", self)
        startAction.triggered.connect(self._reconstruction_start)

        menu_bar = self.menuBar()
        reconstruction_menu = menu_bar.addMenu("Reconstruction")
        reconstruction_menu.addAction(startAction)

    def _reconstruction_start(self):
        """
        Start the reconstruction process.
        """

        self._reset()

        # Create a random image.
        a = np.random.randint(0,256,size=(100,100,3)).astype(np.uint32)
        b = (255 << 24 | a[:,:,0] << 16 | a[:,:,1] << 8 | a[:,:,2]).flatten()
        image = QtGui.QImage(b, 100, 100, QtGui.QImage.Format_RGB32)
        label = QtGui.QLabel(self)
        label.setFixedSize(100, 100)
        label.setPixmap(QtGui.QPixmap(image))

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addWidget(label)
        vbox.addStretch(1)

        hbox = QtGui.QHBoxLayout(self._central_widget)
        hbox.addStretch(1)
        hbox.addLayout(vbox)
        hbox.addStretch(1)
