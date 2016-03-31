import colorsys
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
import pyqtgraph as pg
from PyQt4 import QtGui, QtCore
from Control_Panel_View import Control_Panel_View
from ..reconstruction.Dump_Buffer import Dump_Buffer
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from ..reconstruction.SVD_Reconstructor import SVD_Reconstructor
from ..reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Reconstruction_View, self).__init__(controller, settings)

        pg.setConfigOptions(antialias=True, background=None, foreground="k")

        self._plot_curve_points = self._settings.get("reconstruction_curve_points")
        self._plot_curves = []
        self._plot_data = [[] for vehicle in range(1, self._controller.xbee.number_of_sensors + 1)]

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

        # Create the label for the image.
        self._label = QtGui.QLabel()

        # Create the plot widget.
        self._plot = self._create_plot()
        self._plot.hide()

        # Create the layout and add the widgets.
        hbox_image = QtGui.QHBoxLayout()
        hbox_image.addStretch(1)
        hbox_image.addWidget(self._label)
        hbox_image.addStretch(1)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox_image)
        vbox.addStretch(1)
        vbox.addWidget(self._plot)
        vbox.addStretch(1)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addStretch(1)
        hbox.addLayout(vbox)
        hbox.addStretch(1)

    def _create_plot(self):
        """
        Create the plot widget.
        """

        number_of_sensors = self._controller.xbee.number_of_sensors

        plot_widget = pg.PlotWidget()
        plot_widget.setXRange(0, self._plot_curve_points)
        plot_widget.setLabel("left", "RSSI")
        plot_widget.setLabel("bottom", "Measurement")

        # Create the list of colors for the curves.
        hsv_tuples = [(x * 1.0 / number_of_sensors, 0.5, 0.5) for x in range(number_of_sensors)]
        rgb_tuples = []
        for hsv in hsv_tuples:
            rgb_tuples.append(map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*hsv)))

        # Create the curves for the plot.
        for vehicle in range(1, number_of_sensors + 1):
            curve = plot_widget.plot()
            curve.setData(self._plot_data[vehicle - 1],
                          pen=pg.mkPen(rgb_tuples[vehicle - 1], width=1.5))
            self._plot_curves.append(curve)

        return plot_widget

    def _update_plot(self, packet):
        """
        Update the plot widget.
        """

        for vehicle in range(1, self._controller.xbee.number_of_sensors + 1):
            if len(self._plot_data[vehicle - 1]) > self._plot_curve_points:
                self._plot_data[vehicle - 1].pop(0)

            if packet.get("sensor_id") == vehicle:
                self._plot_data[vehicle - 1].append(packet.get("rssi"))

            self._plot_curves[vehicle - 1].setData(self._plot_data[vehicle - 1])

    def _reconstruction_start(self, reconstructor):
        """
        Start the reconstruction process.
        """

        # Fetch the settings for the reconstruction.
        self._pause_time = self._settings.get("pause_time") * 1000
        self._cmap = self._settings.get("cmap")
        self._interpolation = self._settings.get("interpolation")

        # Set the width and height of the label.
        self._viewer_width, self._viewer_height = self._settings.get("reconstruction_viewer_dimensions")
        self._label.setFixedSize(self._viewer_width, self._viewer_height)

        # Create the buffer.
        options = {
            "filename": "assets/reconstruction_{}.json".format(self._settings.get("filename"))
        }
        self._buffer = Dump_Buffer(options)

        # Create the reconstructor.
        reconstructors = {
            "Least squares": Least_Squares_Reconstructor,
            "SVD": SVD_Reconstructor,
            "Truncated SVD": Truncated_SVD_Reconstructor
        }
        reconstructor_class = reconstructors[reconstructor]
        self._reconstructor = reconstructor_class(self._controller.arguments)

        # Create the weight matrix.
        self._weight_matrix = Weight_Matrix(self._controller.arguments, self._buffer.origin,
                                            self._buffer.size)

        # Execute the reconstruction and visualization.
        self._rssi = []
        self._width, self._height = self._buffer.size
        self._figure = plt.figure(frameon=False, figsize=(self._width, self._height))
        self._axes = self._figure.add_axes([0, 0, 1, 1])
        self._axes.axis("off")
        self._plot.show()
        self._reconstruction_loop()

    def _reconstruction_loop(self):
        """
        Execute the reconstruction to recompute the image when a new measurement is processed.
        """

        if self._buffer.count() > 0:
            packet = self._buffer.get()
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

            self._update_plot(packet)
            QtCore.QTimer.singleShot(self._pause_time, lambda: self._reconstruction_loop())
