import colorsys
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
import pyqtgraph as pg
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from PyQt4 import QtGui, QtCore
from Control_Panel_View import Control_Panel_View
from ..reconstruction.Dataset_Buffer import Dataset_Buffer
from ..reconstruction.Dump_Buffer import Dump_Buffer
from ..reconstruction.Stream_Buffer import Stream_Buffer
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from ..reconstruction.SVD_Reconstructor import SVD_Reconstructor
from ..reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor

class Graph(object):
    def __init__(self, controller, settings):
        """
        Initialize the graph object.
        """

        self._controller = controller
        self._settings = settings

        # Enable antialiassing and use a transparent background with black text/lines.
        pg.setConfigOptions(antialias=True, background=None, foreground="k")

        # Prepare data structures for the graph.
        self._graph = None
        self._graph_curve_points = self._settings.get("reconstruction_curve_points")
        self._graph_curves = []
        self._graph_data = [[] for vehicle in range(1, self._controller.xbee.number_of_sensors + 1)]

    def create(self):
        """
        Create the graph.
        """

        if self._graph is not None:
            return self._graph

        number_of_sensors = self._controller.xbee.number_of_sensors

        self._graph = pg.PlotWidget()
        self._graph.setXRange(0, self._graph_curve_points)
        self._graph.setLabel("left", "RSSI")
        self._graph.setLabel("bottom", "Measurement")

        # Create the list of colors for the curves.
        hsv_tuples = [(x * 1.0 / number_of_sensors, 0.5, 0.5) for x in range(number_of_sensors)]
        rgb_tuples = []
        for hsv in hsv_tuples:
            rgb_tuples.append(map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*hsv)))

        # Create the curves for the graph.
        for vehicle in range(1, number_of_sensors + 1):
            index = vehicle - 1
            curve = self._graph.plot()
            curve.setData(self._graph_data[index], pen=pg.mkPen(rgb_tuples[index], width=1.5))
            self._graph_curves.append(curve)

        return self._graph

    def update(self, packet):
        """
        Update the graph with information in `packet`.
        """

        for vehicle in range(1, self._controller.xbee.number_of_sensors + 1):
            index = vehicle - 1

            if len(self._graph_data[index]) > self._graph_curve_points:
                self._graph_data[index].pop(0)

            if packet.get("sensor_id") == vehicle:
                self._graph_data[index].append(packet.get("rssi"))

            self._graph_curves[index].setData(self._graph_data[index])

    def clear(self):
        """
        Clear the graph.
        """

        for index in range(len(self._graph_data)):
            self._graph_data[index] = []

class Table(object):
    def __init__(self):
        """
        Initialize the table object.
        """

        self._table = None

    def create(self):
        """
        Create the table.
        """

        if self._table is not None:
            return self._table

        column_labels = ["Vehicle", "Source location", "Destination location", "RSSI"]

        self._table = QtGui.QTableWidget()
        self._table.setRowCount(0)
        self._table.setColumnCount(len(column_labels))
        self._table.setHorizontalHeaderLabels(column_labels)
        self._table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        horizontalHeader = self._table.horizontalHeader()
        for index in range(len(column_labels)):
            horizontalHeader.setResizeMode(index, QtGui.QHeaderView.Stretch)

        return self._table

    def update(self, packet):
        """
        Update the table with information in `packet`.
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

    def clear(self):
        """
        Clear the table.
        """

        for index in reversed(range(self._table.rowCount())):
            self._table.removeRow(index)

class Source(object):
    DATASET = "Dataset"
    DUMP = "Dump"
    STREAM = "Stream"

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

        sources = [Source.DATASET, Source.DUMP, Source.STREAM]
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

        # Create the image.
        figure = plt.figure(frameon=False)
        self._axes = figure.add_axes([0, 0, 1, 1])
        self._axes.axis("off")
        self._canvas = FigureCanvas(figure)

        # Create the graph and table.
        self._graph = Graph(self._controller, self._settings)
        self._table = Table()

        # Create the tab widget.
        tabs = QtGui.QTabWidget()
        tabs.addTab(self._graph.create(), "Graph")
        tabs.addTab(self._table.create(), "Table")

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._canvas)
        hbox.addStretch(1)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addWidget(tabs)

    def _refresh_input_boxes(self, source):
        """
        Enable or disable the input boxes depending on the source.
        """

        for input_box in self._input_boxes.itervalues():
            input_box.setEnabled(source == Source.STREAM)

    def _start(self, source, reconstructor):
        """
        Start the reconstruction process.
        """

        # Fetch the settings for the reconstruction.
        self._pause_time = self._settings.get("pause_time") * 1000
        self._cmap = self._settings.get("cmap")
        self._interpolation = self._settings.get("interpolation")

        # Create the buffer depending on the source.
        if source == Source.DATASET:
            options = {
                "file": "assets/dataset_{}.csv".format(self._settings.get("dataset_file"))
            }
            self._buffer = Dataset_Buffer(options)
        elif source == Source.DUMP:
            options = {
                "file": "assets/dump_{}.json".format(self._settings.get("dump_file"))
            }
            self._buffer = Dump_Buffer(options)
        elif source == Source.STREAM:
            origin_x = int(self._input_boxes["origin_x"].text())
            origin_y = int(self._input_boxes["origin_y"].text())
            size_x = int(self._input_boxes["size_x"].text())
            size_y = int(self._input_boxes["size_y"].text())

            if size_x == 0 or size_y == 0:
                QtGui.QMessageBox.critical(self._controller.central_widget, "Invalid network dimensions",
                                           "The network dimensions must be nonzero.")
                return

            options = {
                "number_of_sensors": self._controller.xbee.number_of_sensors,
                "origin": [origin_x, origin_y],
                "size": [size_x, size_y]
            }
            self._buffer = Stream_Buffer(options)
            self._controller.xbee.set_buffer(self._buffer)

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

        # Clear the graph and table.
        self._graph.clear()
        self._table.clear()

        # Execute the reconstruction and visualization.
        self._rssi = []
        self._loop()

    def _loop(self):
        """
        Execute the reconstruction loop.
        """

        # If no packets are available yet, wait for them to arrive.
        if self._buffer.count() == 0:
            QtCore.QTimer.singleShot(self._pause_time, self._loop)
            return

        packet = self._buffer.get()

        # Update the graph and table with the data from the packet.
        self._graph.update(packet)
        self._table.update(packet)

        # Only use packets with valid source and destination locations.
        if not packet.get("from_valid") or not packet.get("to_valid"):
            QtCore.QTimer.singleShot(self._pause_time, self._loop)
            return

        source = (packet.get("from_latitude"), packet.get("from_longitude"))
        destination = (packet.get("to_latitude"), packet.get("to_longitude"))

        # If the weight matrix has been updated, store the RSSI value and
        # redraw the image if the weight matrix is complete.
        if self._weight_matrix.update(source, destination) is not None:
            self._rssi.append(packet.get("rssi"))

            if self._weight_matrix.check():
                pixels = self._reconstructor.execute(self._weight_matrix.output(), self._rssi)

                # Render and draw the image with Matplotlib.
                self._axes.axis("off")
                self._axes.imshow(pixels.reshape(self._buffer.size), cmap=self._cmap,
                                  origin="lower", interpolation=self._interpolation)
                self._canvas.draw()

                # Delete the image from memory now that it is drawn.
                self._axes.cla()

        QtCore.QTimer.singleShot(self._pause_time, self._loop)
