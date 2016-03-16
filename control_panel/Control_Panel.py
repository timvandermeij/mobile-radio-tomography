# TODO: split into multiple files

import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
from ..core.USB_Manager import USB_Manager
from ..reconstruction.Dump_Reader import Dump_Reader
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from ..reconstruction.SVD_Reconstructor import SVD_Reconstructor
from ..reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor
from ..settings import Arguments
from PyQt4 import QtCore, QtGui

class Control_Panel_View_Name(object):
    LOADING = 1
    RECONSTRUCTION = 2

class Control_Panel_View(object):
    def __init__(self, controller):
        """
        Initialize the control panel view.
        """

        self._controller = controller

    def clear(self):
        """
        Clear the view, thereby deleting any existing widgets.
        """

        layout = self._controller.central_widget.layout()

        # Delete all widgets in the layout.
        if layout is not None:
            for item in reversed(range(layout.count())):
                widget = layout.itemAt(item).widget()
                if widget is not None:
                    widget.setParent(None)

        # Delete the layout itself.
        QtCore.QObjectCleanupHandler().add(layout)

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def show(self):
        """
        Show the reconstruction view.
        """

        # Create the toolbar.
        toolbar = self._controller.window.addToolBar("Reconstruction")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar {spacing: 8px;}")

        reconstructor_label = QtGui.QLabel("Reconstructor:")
        reconstructor_box = QtGui.QComboBox()
        reconstructor_box.addItems(["Least squares", "SVD", "Truncated SVD"])
        reconstructor_box.setCurrentIndex(2)
        reconstructor_action = QtGui.QAction(QtGui.QIcon("assets/start.png"), "Start",
                                             self._controller.central_widget)
        reconstructor_action.triggered.connect(
            lambda: self._reconstruction_start(str(reconstructor_box.currentText()))
        )

        toolbar.addWidget(reconstructor_label)
        toolbar.addWidget(reconstructor_box)
        toolbar.addAction(reconstructor_action)

    def _reconstruction_start(self, reconstructor):
        """
        Start the reconstruction process.
        """

        self.clear()

        # Create the label for the image.
        self._label = QtGui.QLabel()

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addWidget(self._label)
        vbox.addStretch(1)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addStretch(1)
        hbox.addLayout(vbox)
        hbox.addStretch(1)

        # Fetch the settings for the reconstruction.
        reconstruction_settings = self._controller.arguments.get_settings("reconstruction")
        self._pause_time = reconstruction_settings.get("pause_time") * 1000
        self._cmap = reconstruction_settings.get("cmap")
        self._interpolation = reconstruction_settings.get("interpolation")

        # Set the width and height of the label.
        control_panel_settings = self._controller.arguments.get_settings("control_panel")
        self._viewer_width, self._viewer_height = control_panel_settings.get("viewer_dimensions")
        self._label.setFixedSize(self._viewer_width, self._viewer_height)

        # Create the reader.
        filename = reconstruction_settings.get("filename")
        self._reader = Dump_Reader("assets/reconstruction_{}.json".format(filename))

        # Create the reconstructor.
        reconstructors = {
            "Least squares": Least_Squares_Reconstructor,
            "SVD": SVD_Reconstructor,
            "Truncated SVD": Truncated_SVD_Reconstructor
        }
        reconstructor_class = reconstructors[reconstructor]
        self._reconstructor = reconstructor_class(self._controller.arguments)

        # Create the weight matrix.
        self._weight_matrix = Weight_Matrix(self._controller.arguments, self._reader.get_origin(),
                                            self._reader.get_size())

        # Execute the reconstruction and visualization.
        self._rssi = []
        self._width, self._height = self._reader.get_size()
        self._figure = plt.figure(frameon=False, figsize=(self._width, self._height))
        self._axes = self._figure.add_axes([0, 0, 1, 1])
        self._axes.axis("off")
        self._reconstruction_loop()

    def _reconstruction_loop(self):
        """
        Execute the reconstruction to recompute the image when a new measurement is processed.
        """

        if self._reader.count_packets() > 0:
            packet = self._reader.get_packet()
            self._rssi.append(packet.get("rssi"))
            source = (packet.get("from_latitude"), packet.get("from_longitude"))
            destination = (packet.get("to_latitude"), packet.get("to_longitude"))
            self._weight_matrix.update(source, destination)
            if self._weight_matrix.check():
                pixels = self._reconstructor.execute(self._weight_matrix.output(), self._rssi)

                # Render the image with Matplotlib.
                self._axes.imshow(pixels.reshape((self._width, self._height)), cmap=self._cmap,
                                  origin="lower", interpolation=self._interpolation)
                self._figure.canvas.draw()

                # Draw the image with Qt.
                size = self._figure.canvas.size()
                image = QtGui.QImage(self._figure.canvas.buffer_rgba(), size.width(),
                                     size.height(), QtGui.QImage.Format_ARGB32)
                scaled_image = image.scaled(self._viewer_width, self._viewer_height)
                self._label.setPixmap(QtGui.QPixmap(scaled_image))

            QtCore.QTimer.singleShot(self._pause_time, self._reconstruction_loop)

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

class Control_Panel_Controller(object):
    def __init__(self, central_widget, window):
        """
        Initialize the control panel controller.
        """

        # Set the central widget and window for loading views.
        self.central_widget = central_widget
        self.window = window

        # Create arguments (for obtaining various settings in views)
        # and a USB manager (for checking insertion of XBee devices).
        self.arguments = Arguments("settings.json", [])
        self.usb_manager = USB_Manager()

        # Show the loading view (default).
        self.show_view(Control_Panel_View_Name.LOADING)

    def show_view(self, name):
        """
        Show a new view, identified by `name`, and clear the current view.
        """

        views = {
            Control_Panel_View_Name.LOADING: Control_Panel_Loading_View,
            Control_Panel_View_Name.RECONSTRUCTION: Control_Panel_Reconstruction_View
        }

        if name not in views:
            raise ValueError("Unknown view name specified.")

        view = views[name](self)
        view.clear()
        view.show()

class Control_Panel_Window(QtGui.QMainWindow):
    def __init__(self):
        """
        Initialize the control panel window.
        """

        super(Control_Panel_Window, self).__init__()

        # Set the dimensions, title and icon of the window.
        self.setGeometry(0, 0, 800, 600)
        self.setWindowTitle("Mobile radio tomography")
        self.setWindowIcon(QtGui.QIcon("assets/mobile-radio-tomography.png"))

        # Center the window.
        resolution = QtGui.QDesktopWidget().screenGeometry()
        frame_size = self.frameSize()
        self.move(resolution.width() / 2 - frame_size.width() / 2,
                  resolution.height() / 2 - frame_size.height() / 2)

        # Create a central widget.
        central_widget = QtGui.QWidget()
        self.setCentralWidget(central_widget)

        # Create a controller.
        controller = Control_Panel_Controller(central_widget, self)
