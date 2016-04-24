# TODO:
# - Implement more reconstructors: Tikhonov and total variation
# - Investigate canvas flipping
# - Average measurements of the same link
# - Tweak ellipse width/singular values/model (based on grid experiments)
# - Extend calibration procedure for all data sources (change UI for calibrated RSSI)

import json
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
import os.path
import pyqtgraph as pg
import thread
from collections import OrderedDict
from functools import partial
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from PyQt4 import QtGui, QtCore
from Control_Panel_View import Control_Panel_View
from ..reconstruction.Coordinator import Coordinator
from ..reconstruction.Dataset_Buffer import Dataset_Buffer
from ..reconstruction.Dump_Buffer import Dump_Buffer
from ..reconstruction.Stream_Buffer import Stream_Buffer
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

        # Create the curves for the graph.
        color_index = 0
        for vehicle in range(1, self._number_of_sensors + 1):
            index = vehicle - 1

            color = pg.intColor(color_index, hues=len(self._graph_data), maxValue=200)
            color_index += 1

            curve = self._graph.plot()
            curve.setData(self._graph_data[index], pen=pg.mkPen(color, width=1.5))
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

        for curve in self._graph_curves:
            curve.clear()

        self._graph_data = []
        self._graph_curves = []

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

class Dataset_Panel(Panel):
    def __init__(self, parent, settings):
        """
        Initialize the dataset panel object.
        """

        super(Dataset_Panel, self).__init__(parent, settings)

        self._source = Source.DATASET

    def _render(self):
        """
        Render the panel with both the default items and items
        that are specific to this data source.
        """

        input_elements = {
            "dataset_calibration_file": "Calibration file",
            "dataset_file": "File"
        }

        for key, label in input_elements.iteritems():
            widget = QtGui.QWidget()
            widget_layout = QtGui.QHBoxLayout()
            widget_layout.setContentsMargins(0, 0, 0, 0)

            file_box = QtGui.QLineEdit()
            file_box.setText(self._settings.get(key))

            widget_layout.addWidget(file_box)
            widget.setLayout(widget_layout)

            self._register(label, widget, partial(
                lambda file_box: "assets/dataset_{}.csv".format(file_box.text()), file_box
            ))

        super(Dataset_Panel, self)._render()

class Dump_Panel(Panel):
    def __init__(self, parent, settings):
        """
        Initialize the dump panel object.
        """

        super(Dump_Panel, self).__init__(parent, settings)

        self._source = Source.DUMP

    def _render(self):
        """
        Render the panel with both the default items and items
        that are specific to this data source.
        """

        input_elements = {
            "dump_calibration_file": "Calibration file",
            "dump_file": "File"
        }

        for key, label in input_elements.iteritems():
            widget = QtGui.QWidget()
            widget_layout = QtGui.QHBoxLayout()
            widget_layout.setContentsMargins(0, 0, 0, 0)

            file_box = QtGui.QLineEdit()
            file_box.setText(self._settings.get(key))

            widget_layout.addWidget(file_box)
            widget.setLayout(widget_layout)

            self._register(label, widget, partial(
                lambda file_box: "assets/dump_{}.json".format(file_box.text()), file_box
            ))

        super(Dump_Panel, self)._render()

class Stream_Panel(Panel):
    def __init__(self, parent, settings):
        """
        Initialize the stream panel object.
        """

        super(Stream_Panel, self).__init__(parent, settings)

        self._source = Source.STREAM

    def _render(self):
        """
        Render the panel with both the default items and items
        that are specific to this data source.
        """

        # Create the origin and size inputs.
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
                lambda x_box, y_box: [int(x_box.text()), int(y_box.text())], x_box, y_box
            ))

        # Create the record and calibrate checkboxes.
        for label in ["Record", "Calibrate"]:
            checkbox = QtGui.QCheckBox("Yes")
            self._register(label, checkbox, partial(
                lambda checkbox: checkbox.isChecked(), checkbox
            ))

        # Create the calibration file input.
        widget = QtGui.QWidget()
        widget_layout = QtGui.QHBoxLayout()
        widget_layout.setContentsMargins(0, 0, 0, 0)

        file_box = QtGui.QLineEdit()

        widget_layout.addWidget(file_box)
        widget.setLayout(widget_layout)

        self._register("Calibration file", widget, partial(
            lambda file_box: "assets/stream_{}.json".format(file_box.text()), file_box
        ))

        super(Stream_Panel, self)._render()

class Stream_Recorder(object):
    def __init__(self, central_widget=None, options=None):
        """
        Initialize the stream recorder object.

        The stream recorder keeps a copy of every incoming packet when recording mode is
        enabled. When recording is stopped, the captured data is exported to a dump file.
        """

        if central_widget is None:
            raise ValueError("Central widget for the stream recorder has not been provided.")

        if options is None:
            raise ValueError("Options for the stream recorder have not been provided.")

        self._central_widget = central_widget

        self._number_of_sensors = options["number_of_sensors"]
        self._origin = options["origin"]
        self._size = options["size"]

        self._packets = []

    def update(self, packet):
        """
        Update the stream recorder with information in `packet`.
        """

        self._packets.append(packet)

    def export(self):
        """
        Export the packets (along with network information) to a dump file.
        """

        file_name = QtGui.QFileDialog.getSaveFileName(self._central_widget,
                                                      "Export file", os.getcwd(),
                                                      "JSON files (*.json)")

        if file_name == "":
            return

        try:
            with open(file_name, "w") as export_file:
                json.dump({
                    "number_of_sensors": self._number_of_sensors,
                    "origin": self._origin,
                    "size": self._size,
                    "packets": [packet.get_dump() for packet in self._packets]
                }, export_file)
        except IOError as e:
            message = "Could not open file '{}': {}".format(file_name, e.strerror)
            QtGui.QMessageBox.critical(self._central_widget, "File error", message)

class Source(object):
    DATASET = "Dataset"
    DUMP = "Dump"
    STREAM = "Stream"

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def show(self):
        """
        Show the reconstruction view.
        """

        self._running = False
        self._stream_recorder = None

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
        panels.addTab(Dataset_Panel(panels, self._settings), Source.DATASET)
        panels.addTab(Dump_Panel(panels, self._settings), Source.DUMP)
        panels.addTab(Stream_Panel(panels, self._settings), Source.STREAM)

        # Create the toggle button (using the stopped state as default).
        self._toggle_button = QtGui.QPushButton(QtGui.QIcon("assets/start.png"), "Start")
        self._toggle_button.clicked.connect(lambda: self._toggle(panels.currentWidget()))

        # Create the layout and add the widgets.
        vbox_left = QtGui.QVBoxLayout()
        vbox_left.addWidget(panels)
        vbox_left.addWidget(self._toggle_button)

        vbox_right = QtGui.QVBoxLayout()
        vbox_right.addWidget(self._canvas)
        vbox_right.addStretch(1)
        vbox_right.addWidget(tabs)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addLayout(vbox_left)
        hbox.addLayout(vbox_right)

    def _toggle(self, parameters):
        """
        Toggle the state of the reconstruction (start or stop).
        """

        self._running = not self._running

        if self._running:
            self._toggle_button.setIcon(QtGui.QIcon("assets/stop.png"))
            self._toggle_button.setText("Stop")

            self._start(parameters)
        else:
            self._toggle_button.setIcon(QtGui.QIcon("assets/start.png"))
            self._toggle_button.setText("Start")

    def _start(self, parameters):
        """
        Start the reconstruction process with all parameters from the panel.
        """

        # Fetch the settings for the reconstruction.
        self._pause_time = self._settings.get("pause_time") * 1000
        self._cmap = self._settings.get("cmap")
        self._interpolation = self._settings.get("interpolation")
        self._chunk_size = self._settings.get("chunk_size")

        # Create the buffer and reconstructor.
        try:
            self._create_buffer(parameters)
            self._create_reconstructor(parameters)
        except Exception as exception:
            QtGui.QMessageBox.critical(self._controller.central_widget, "Initialization error",
                                       exception.message)
            self._toggle(parameters)
            return

        # Create the coordinator.
        self._coordinator = Coordinator(self._controller.arguments, self._buffer)

        # Clear the graph and table and setup the graph.
        self._graph.clear()
        self._graph.setup(self._buffer)
        self._table.clear()

        # Clear the image.
        self._axes.cla()
        self._axes.axis("off")
        self._canvas.draw()

        # Execute the reconstruction and visualization.
        self._chunk_count = 0
        self._loop()

    def _create_buffer(self, parameters):
        """
        Create the buffer for the reconstruction process (depending on the data source).
        """

        if parameters.source == Source.DATASET or parameters.source == Source.DUMP:
            calibration_file = parameters.get("Calibration file")
            file = parameters.get("File")

            for field in [calibration_file, file]:
                if not os.path.exists(field):
                    raise OSError("File '{}' does not exist.".format(field))

            buffer_class = Dataset_Buffer if parameters.source == Source.DATASET else Dump_Buffer
            self._buffer = buffer_class({
                "calibration_file": calibration_file,
                "file": file
            })
        elif parameters.source == Source.STREAM:
            origin = parameters.get("Origin")
            size = parameters.get("Size")
            record = parameters.get("Record")
            calibrate = parameters.get("Calibrate")
            calibration_file = parameters.get("Calibration file")

            if not all(dimension > 0 for dimension in size):
                raise ValueError("The network dimensions must be greater than zero.")

            if not calibrate and not os.path.exists(calibration_file):
                raise OSError("File '{}' does not exist.".format(calibration_file))

            self._buffer = Stream_Buffer({
                "number_of_sensors": self._controller.xbee.number_of_sensors,
                "origin": origin,
                "size": size,
                "calibrate": calibrate,
                "calibration_file": calibration_file
            })
            self._controller.xbee.set_buffer(self._buffer)

            if record or calibrate:
                # Create a stream recorder instance to record all incoming packets.
                # The existence of this object is enough to let the loop handle the
                # recording process.
                self._stream_recorder = Stream_Recorder(self._controller.central_widget, {
                    "number_of_sensors": self._controller.xbee.number_of_sensors,
                    "origin": origin,
                    "size": size
                })

    def _create_reconstructor(self, parameters):
        """
        Create the reconstructor for the reconstruction process.
        """

        reconstructors = {
            "Least squares": Least_Squares_Reconstructor,
            "SVD": SVD_Reconstructor,
            "Truncated SVD": Truncated_SVD_Reconstructor
        }
        reconstructor_class = reconstructors[parameters.get("Reconstructor")]
        self._reconstructor = reconstructor_class(self._controller.arguments)

    def _loop(self):
        """
        Execute the reconstruction loop.
        """

        # Stop if the stop button has been pressed.
        if not self._running:
            if self._stream_recorder is not None:
                self._stream_recorder.export()
                self._stream_recorder = None

            return

        # If no packets are available yet, wait for them to arrive.
        if self._buffer.count() == 0:
            QtCore.QTimer.singleShot(self._pause_time, self._loop)
            return

        packet = self._buffer.get()

        # Update the graph, table and stream recorder (if applicable) with the packet.
        self._graph.update(packet)
        self._table.update(packet)
        if self._stream_recorder is not None:
            self._stream_recorder.update(packet)

        # Only use packets with valid source and destination locations.
        if not packet.get("from_valid") or not packet.get("to_valid"):
            QtCore.QTimer.singleShot(self._pause_time, self._loop)
            return

        # We attempt to reconstruct an image when the coordinator successfully
        # updated the weight matrix and the RSSI vector and when we have obtained
        # the required number of measurements to fill a chunk.
        if self._coordinator.update(packet):
            self._chunk_count += 1
            if self._chunk_count >= self._chunk_size:
                self._chunk_count = 0

                thread.start_new_thread(self._render, ())

        QtCore.QTimer.singleShot(self._pause_time, self._loop)

    def _render(self):
        """
        Render and draw the image using Matplotlib. This runs in a separate thread.
        """

        try:
            pixels = self._reconstructor.execute(self._coordinator.get_weight_matrix(),
                                                 self._coordinator.get_rssi_vector())

            self._axes.axis("off")
            self._axes.imshow(pixels.reshape(self._buffer.size), cmap=self._cmap,
                              origin="lower", interpolation=self._interpolation)
            self._canvas.draw()

            # Delete the image from memory now that it is drawn.
            self._axes.cla()
        except:
            # There is not enough data yet for the reconstruction algorithm.
            pass
