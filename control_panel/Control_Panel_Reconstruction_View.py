import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
from PyQt4 import QtGui, QtCore
from Control_Panel_View import Control_Panel_View
from ..reconstruction.Dump_Reader import Dump_Reader
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from ..reconstruction.SVD_Reconstructor import SVD_Reconstructor
from ..reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def show(self):
        """
        Show the reconstruction view.
        """

        self._add_menu_bar()

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

        self._controller.window._toolbar = toolbar

    def _reconstruction_start(self, reconstructor):
        """
        Start the reconstruction process.
        """

        self.clear()
        self.show()

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

            QtCore.QTimer.singleShot(self._pause_time, lambda: self._reconstruction_loop())
