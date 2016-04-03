import colorsys
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
import pyqtgraph as pg
from PyQt4 import QtGui, QtCore
from Control_Panel_View import Control_Panel_View
from ..reconstruction.Dump_Buffer import Dump_Buffer
from ..reconstruction.Stream_Buffer import Stream_Buffer
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from ..reconstruction.SVD_Reconstructor import SVD_Reconstructor
from ..reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Reconstruction_View, self).__init__(controller, settings)

        pg.setConfigOptions(antialias=True, background=None, foreground="k")

        self._graph_curve_points = self._settings.get("reconstruction_curve_points")
        self._graph_curves = []
        self._graph_data = [[] for vehicle in range(1, self._controller.xbee.number_of_sensors + 1)]

    def show(self):
        """
        Show the reconstruction view.
        """

        self._add_menu_bar()

        # Create the toolbar.
        toolbar = self._controller.window.addToolBar("Reconstruction")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar {spacing: 8px;}")

        sources = ["File", "Stream"]
        source_label = QtGui.QLabel("Source:")
        source_box = QtGui.QComboBox()
        source_box.addItems(sources)
        source_box.currentIndexChanged["QString"].connect(self._refresh_input_boxes)

        reconstructor_label = QtGui.QLabel("Reconstructor:")
        reconstructor_box = QtGui.QComboBox()
        reconstructor_box.addItems(["Least squares", "SVD", "Truncated SVD"])
        reconstructor_box.setCurrentIndex(2)

        origin_label = QtGui.QLabel("Network origin:")
        size_label = QtGui.QLabel("Network size:")

        self._input_boxes = {
            "origin_x": QtGui.QLineEdit(),
            "origin_y": QtGui.QLineEdit(),
            "size_x": QtGui.QLineEdit(),
            "size_y": QtGui.QLineEdit()
        }
        for input_box in self._input_boxes.itervalues():
            input_box.setText("0")

        self._refresh_input_boxes(sources[0])

        start_action = QtGui.QAction(QtGui.QIcon("assets/start.png"), "Start",
                                     self._controller.central_widget)
        start_action.triggered.connect(
            lambda: self._start(str(source_box.currentText()),
                                str(reconstructor_box.currentText()))
        )

        toolbar.addWidget(source_label)
        toolbar.addWidget(source_box)
        toolbar.addWidget(reconstructor_label)
        toolbar.addWidget(reconstructor_box)
        toolbar.addWidget(origin_label)
        toolbar.addWidget(self._input_boxes["origin_x"])
        toolbar.addWidget(self._input_boxes["origin_y"])
        toolbar.addWidget(size_label)
        toolbar.addWidget(self._input_boxes["size_x"])
        toolbar.addWidget(self._input_boxes["size_y"])
        toolbar.addAction(start_action)

        self._controller.window._toolbar = toolbar

        # Create the label for the image.
        self._viewer_width, self._viewer_height = self._settings.get("reconstruction_viewer_dimensions")
        self._label = QtGui.QLabel()
        self._label.setFixedSize(self._viewer_width, self._viewer_height)

        # Create the graph and table.
        graph = self._create_graph()
        self._table = self._create_table()

        # Create the tab widget.
        tabs = QtGui.QTabWidget()
        tabs.addTab(graph, "Graph")
        tabs.addTab(self._table, "Table")

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._label)
        hbox.addStretch(1)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addWidget(tabs)
        vbox.addStretch(1)

    def _refresh_input_boxes(self, source):
        """
        Enable or disable the input boxes depending on the source.
        """

        for input_box in self._input_boxes.itervalues():
            input_box.setDisabled(source == "File")

    def _create_graph(self):
        """
        Create the graph for signal strength (RSSI) values.
        """

        number_of_sensors = self._controller.xbee.number_of_sensors

        graph = pg.PlotWidget()
        graph.setXRange(0, self._graph_curve_points)
        graph.setLabel("left", "RSSI")
        graph.setLabel("bottom", "Measurement")

        # Create the list of colors for the curves.
        hsv_tuples = [(x * 1.0 / number_of_sensors, 0.5, 0.5) for x in range(number_of_sensors)]
        rgb_tuples = []
        for hsv in hsv_tuples:
            rgb_tuples.append(map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*hsv)))

        # Create the curves for the graph.
        for vehicle in range(1, number_of_sensors + 1):
            curve = graph.plot()
            curve.setData(self._graph_data[vehicle - 1],
                          pen=pg.mkPen(rgb_tuples[vehicle - 1], width=1.5))
            self._graph_curves.append(curve)

        return graph

    def _update_graph(self, packet):
        """
        Update the graph for signal strength (RSSI) values.
        """

        for vehicle in range(1, self._controller.xbee.number_of_sensors + 1):
            if len(self._graph_data[vehicle - 1]) > self._graph_curve_points:
                self._graph_data[vehicle - 1].pop(0)

            if packet.get("sensor_id") == vehicle:
                self._graph_data[vehicle - 1].append(packet.get("rssi"))

            self._graph_curves[vehicle - 1].setData(self._graph_data[vehicle - 1])

    def _create_table(self):
        """
        Create the table for the incoming XBee packets.
        """

        column_labels = ["Vehicle", "Source location", "Destination location", "RSSI"]

        table = QtGui.QTableWidget()
        table.setRowCount(0)
        table.setColumnCount(len(column_labels))
        table.setHorizontalHeaderLabels(column_labels)
        table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        horizontalHeader = table.horizontalHeader()
        for i in range(len(column_labels)):
            horizontalHeader.setResizeMode(i, QtGui.QHeaderView.Stretch)

        return table

    def _update_table(self, packet):
        """
        Update the table for the incoming XBee packets.
        """

        # Collect and format the data.
        vehicle = str(packet.get("sensor_id"))
        source_location = "({}, {})".format(packet.get("from_latitude"), packet.get("from_longitude"))
        destination_location = "({}, {})".format(packet.get("to_latitude"), packet.get("to_longitude"))
        rssi = str(packet.get("rssi"))

        # Append a new table row.
        position = self._table.rowCount()
        self._table.insertRow(position)
        self._table.setItem(position, 0, QtGui.QTableWidgetItem(vehicle))
        self._table.setItem(position, 1, QtGui.QTableWidgetItem(source_location))
        self._table.setItem(position, 2, QtGui.QTableWidgetItem(destination_location))
        self._table.setItem(position, 3, QtGui.QTableWidgetItem(rssi))

        # Indicate the validity of the source and destination locations.
        green = QtGui.QColor("#8BD672")
        red = QtGui.QColor("#FA6969")
        self._table.item(position, 1).setBackground(green if packet.get("from_valid") else red)
        self._table.item(position, 2).setBackground(green if packet.get("to_valid") else red)

        # Automatically scroll the table to the bottom.
        self._table.scrollToBottom()

    def _start(self, source, reconstructor):
        """
        Start the reconstruction process.
        """

        # Fetch the settings for the reconstruction.
        self._pause_time = self._settings.get("pause_time") * 1000
        self._cmap = self._settings.get("cmap")
        self._interpolation = self._settings.get("interpolation")

        # Create the buffer depending on the source (file or stream).
        if source == "File":
            options = {
                "filename": "assets/reconstruction_{}.json".format(self._settings.get("filename"))
            }
            self._buffer = Dump_Buffer(options)
        elif source == "Stream":
            origin_x = int(self._input_boxes["origin_x"].text())
            origin_y = int(self._input_boxes["origin_y"].text())
            size_x = int(self._input_boxes["size_x"].text())
            size_y = int(self._input_boxes["size_y"].text())

            options = {
                "origin": [origin_x, origin_y],
                "size": [size_x, size_y]
            }
            self._buffer = Stream_Buffer(options)

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
        self._loop()

    def _loop(self):
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

            self._update_graph(packet)
            self._update_table(packet)

            QtCore.QTimer.singleShot(self._pause_time, lambda: self._loop())
