# TODO:
# - Dataset performance (reading with progress bar or packet generation on demand)
# - Implement more reconstructors: Tikhonov and total variation
# - Faster reconstruction: epsilon instead of zero
# - Render after a chunk of measurements of a certain size, not after each measurement
# - Remove old data to keep the weight matrix and RSSI vector compact
# - Remove timers where possible: use the availability of data chunks instead
# - Investigate canvas flipping
# - Implement dump recorder
# - Average measurements of the same link

import colorsys
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
import os.path
import pyqtgraph as pg
from collections import OrderedDict
from functools import partial
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
    def __init__(self, settings):
        """
        Initialize the graph object.
        """

        self._settings = settings

        # Enable antialiassing and use a transparent background with black text/lines.
        pg.setConfigOptions(antialias=True, background=None, foreground="k")

        # Prepare data structures for the graph.
        self._number_of_sensors = 0
        self._graph = None
        self._graph_curve_points = self._settings.get("reconstruction_curve_points")
        self._graph_curves = []
        self._graph_data = []

    def setup(self, buffer):
        """
        Setup the graph with the number of sensors from the buffer.
        """

        self._number_of_sensors = buffer.number_of_sensors

        # Create the data lists for the graph.
        self._graph_data = [[] for vehicle in range(1, self._number_of_sensors + 1)]

        # Create the list of colors for the curves.
        hsv_tuples = [(x * 1.0 / self._number_of_sensors, 0.5, 0.5) for x in range(self._number_of_sensors)]
        rgb_tuples = []
        for hsv in hsv_tuples:
            rgb_tuples.append(map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*hsv)))

        # Create the curves for the graph.
        for vehicle in range(1, self._number_of_sensors + 1):
            index = vehicle - 1
            curve = self._graph.plot()
            curve.setData(self._graph_data[index], pen=pg.mkPen(rgb_tuples[index], width=1.5))
            self._graph_curves.append(curve)

    def create(self):
        """
        Create the graph.
        """

        if self._graph is not None:
            return self._graph

        self._graph = pg.PlotWidget()
        self._graph.setXRange(0, self._graph_curve_points)
        self._graph.setLabel("left", "RSSI")
        self._graph.setLabel("bottom", "Measurement")

        return self._graph

    def update(self, packet):
        """
        Update the graph with information in `packet`.
        """

        for vehicle in range(1, self._number_of_sensors + 1):
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

class Panel(QtGui.QTableWidget):
    def __init__(self, parent, settings):
        """
        Initialize the panel object.
        """

        QtGui.QTableWidget.__init__(self, parent)

        self._settings = settings
        self._source = None

        # Maintain an object that maps a label to a lambda function responsible
        # for returning the value of the widget. This is used to fetch all entered
        # values in a structured manner when the reconstruction process is started.
        self._data = {}

        # Create the key and value columns.
        self.setColumnCount(2)

        # Let the columns take up the entire width of the table.
        for index in range(2):
            self.horizontalHeader().setResizeMode(index, QtGui.QHeaderView.Stretch)

        # Hide the horizontal and vertical headers.
        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        # Populate the panel with default items.
        self._items = OrderedDict()

        reconstructor = QtGui.QComboBox()
        reconstructor.addItems(["Least squares", "SVD", "Truncated SVD"])
        reconstructor.setCurrentIndex(2)

        self._register("Reconstructor", reconstructor,
                       partial(lambda reconstructor: str(reconstructor.currentText()), reconstructor))
        self._render()

    @property
    def source(self):
        """
        Return the data source corresponding to this panel.
        """

        return self._source

    def get(self, label):
        """
        Get the value of the widget identified by its `label` using
        the associated lambda function.
        """

        if label not in self._data:
            raise ValueError("Lambda function for label '{}' has not been registered".format(label))

        return self._data[label]()

    def _register(self, label, widget, lambda_function):
        """
        Register an item for the table with a `label`, a `widget` and a
        `lambda_function` that takes care of fetching the value of the widget.
        """

        self._items[label] = widget
        self._data[label] = lambda_function

    def _render(self):
        """
        Render the panel with all registered items.
        """

        for label, widget in self._items.iteritems():
            position = self.rowCount()

            label = QtGui.QTableWidgetItem("{}:".format(label))
            label.setFlags(label.flags() & ~QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsSelectable)

            self.insertRow(position)
            self.setItem(position, 0, label)
            self.setCellWidget(position, 1, widget)

class DatasetPanel(Panel):
    def __init__(self, parent, settings):
        """
        Initialize the dataset panel object.
        """

        super(DatasetPanel, self).__init__(parent, settings)

        self._source = Source.DATASET

    def _render(self):
        """
        Render the panel with both the default items and items
        that are specific to this data source.
        """

        widget = QtGui.QWidget()

        widget_layout = QtGui.QHBoxLayout()
        widget_layout.setContentsMargins(0, 0, 0, 0)

        file_box = QtGui.QLineEdit()
        file_box.setText(self._settings.get("dataset_file"))

        widget_layout.addWidget(file_box)
        widget.setLayout(widget_layout)

        self._register("File", widget, partial(
            lambda file_box: "assets/dataset_{}.csv".format(file_box.text()), file_box)
        )

        super(DatasetPanel, self)._render()

class DumpPanel(Panel):
    def __init__(self, parent, settings):
        """
        Initialize the dump panel object.
        """

        super(DumpPanel, self).__init__(parent, settings)

        self._source = Source.DUMP

    def _render(self):
        """
        Render the panel with both the default items and items
        that are specific to this data source.
        """

        widget = QtGui.QWidget()

        widget_layout = QtGui.QHBoxLayout()
        widget_layout.setContentsMargins(0, 0, 0, 0)

        file_box = QtGui.QLineEdit()
        file_box.setText(self._settings.get("dump_file"))

        widget_layout.addWidget(file_box)
        widget.setLayout(widget_layout)

        self._register("File", widget, partial(
            lambda file_box: "assets/dump_{}.json".format(file_box.text()), file_box)
        )

        super(DumpPanel, self)._render()

class StreamPanel(Panel):
    def __init__(self, parent, settings):
        """
        Initialize the stream panel object.
        """

        super(StreamPanel, self).__init__(parent, settings)

        self._source = Source.STREAM

    def _render(self):
        """
        Render the panel with both the default items and items
        that are specific to this data source.
        """

        for label in ["Origin", "Size"]:
            widget = QtGui.QWidget()

            widget_layout = QtGui.QHBoxLayout()
            widget_layout.setContentsMargins(0, 0, 0, 0)

            x_box = QtGui.QLineEdit()
            x_box.setText("0")
            y_box = QtGui.QLineEdit()
            y_box.setText("0")

            widget_layout.addWidget(x_box)
            widget_layout.addWidget(y_box)
            widget.setLayout(widget_layout)

            self._register(label, widget, partial(
                lambda x_box, y_box: [int(x_box.text()), int(y_box.text())], x_box, y_box)
            )

        super(StreamPanel, self)._render()

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

        # Create the image.
        figure = plt.figure(frameon=False)
        self._axes = figure.add_axes([0, 0, 1, 1])
        self._axes.axis("off")
        self._canvas = FigureCanvas(figure)

        # Create the graph and table.
        self._graph = Graph(self._settings)
        self._table = Table()

        # Create the tab widget.
        tabs = QtGui.QTabWidget()
        tabs.addTab(self._graph.create(), "Graph")
        tabs.addTab(self._table.create(), "Table")

        # Create the panels.
        panels = QtGui.QTabWidget()
        panels.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        panels.addTab(DatasetPanel(panels, self._settings), Source.DATASET)
        panels.addTab(DumpPanel(panels, self._settings), Source.DUMP)
        panels.addTab(StreamPanel(panels, self._settings), Source.STREAM)

        # Create the start button.
        start_button = QtGui.QPushButton(QtGui.QIcon("assets/start.png"), "Start")
        start_button.clicked.connect(lambda: self._start(panels.currentWidget()))

        # Create the layout and add the widgets.
        vbox_left = QtGui.QVBoxLayout()
        vbox_left.addWidget(panels)
        vbox_left.addWidget(start_button)

        vbox_right = QtGui.QVBoxLayout()
        vbox_right.addWidget(self._canvas)
        vbox_right.addStretch(1)
        vbox_right.addWidget(tabs)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addLayout(vbox_left)
        hbox.addLayout(vbox_right)

    def _start(self, parameters):
        """
        Start the reconstruction process with all parameters from the panel.
        """

        # Fetch the settings for the reconstruction.
        self._pause_time = self._settings.get("pause_time") * 1000
        self._cmap = self._settings.get("cmap")
        self._interpolation = self._settings.get("interpolation")

        # Create the buffer depending on the source.
        if parameters.source == Source.DATASET or parameters.source == Source.DUMP:
            file = parameters.get("File")

            if not os.path.exists(file):
                QtGui.QMessageBox.critical(self._controller.central_widget, "Invalid file",
                                           "File '{}' does not exist.".format(file))
                return

            buffer_class = Dataset_Buffer if parameters.source == Source.DATASET else Dump_Buffer
            self._buffer = buffer_class({
                "file": file
            })
        elif parameters.source == Source.STREAM:
            origin = parameters.get("Origin")
            size = parameters.get("Size")

            if not all(dimension > 0 for dimension in size):
                QtGui.QMessageBox.critical(self._controller.central_widget, "Invalid size",
                                           "The network dimensions must be greater than zero.")
                return

            self._buffer = Stream_Buffer({
                "number_of_sensors": self._controller.xbee.number_of_sensors,
                "origin": origin,
                "size": size
            })
            self._controller.xbee.set_buffer(self._buffer)

        # Create the reconstructor.
        reconstructors = {
            "Least squares": Least_Squares_Reconstructor,
            "SVD": SVD_Reconstructor,
            "Truncated SVD": Truncated_SVD_Reconstructor
        }
        reconstructor_class = reconstructors[parameters.get("Reconstructor")]
        self._reconstructor = reconstructor_class(self._controller.arguments)

        # Create the weight matrix.
        self._weight_matrix = Weight_Matrix(self._controller.arguments, self._buffer.origin,
                                            self._buffer.size)

        # Setup the graph and clear the graph and table.
        self._graph.setup(self._buffer)
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
