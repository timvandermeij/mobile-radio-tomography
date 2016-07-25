# Core imports
import datetime
import json
import thread
import os

# matplotlib imports
import matplotlib
try:
    matplotlib.use("Qt4Agg")
except ValueError as e:
    raise ImportError("Could not load matplotlib backend: {}".format(e.message))
finally:
    import matplotlib.pyplot as plt

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

# NumPy imports
import numpy as np

# Qt imports
import pyqtgraph as pg
from PyQt4 import QtGui, QtCore

# Package imports
from Control_Panel_Settings_Widgets import SettingsTableWidget
from Control_Panel_View import Control_Panel_View
from ..core.Import_Manager import Import_Manager
from ..reconstruction.Coordinator import Coordinator
from ..reconstruction.Dataset_Buffer import Dataset_Buffer
from ..reconstruction.Dump_Buffer import Dump_Buffer
from ..reconstruction.Stream_Buffer import Stream_Buffer

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
    def __init__(self, settings):
        """
        Initialize the table object.
        """

        self._table = None
        self._limit = settings.get("reconstruction_table_limit")

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

        # Limit the table to a fixed number of rows.
        if self._table.rowCount() >= self._limit:
            self._table.removeRow(0)

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

class Stream_Recorder(object):
    def __init__(self, controller=None, settings=None):
        """
        Initialize the stream recorder object.

        The stream recorder keeps a copy of every incoming packet when recording mode is
        enabled. When recording is stopped, the captured data is exported to a dump file.
        """

        if controller is None:
            raise ValueError("Controller for the stream recorder has not been provided.")

        if settings is None:
            raise ValueError("Settings for the stream recorder have not been provided.")

        self._controller = controller

        self._number_of_sensors = controller.rf_sensor.number_of_sensors
        self._origin = settings.get("stream_network_origin")
        self._size = settings.get("stream_network_size")

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

        file_name = QtGui.QFileDialog.getSaveFileName(self._controller.central_widget,
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
            QtGui.QMessageBox.critical(self._controller.central_widget, "File error", message)

class Stacked_Settings_Form(QtGui.QStackedWidget):
    def __init__(self, arguments, name):
        super(Stacked_Settings_Form, self).__init__()
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Maximum)
        self._arguments = arguments
        self._name = name
        self._forms = {}

    def register_form(self, form):
        """
        Register a handler that updates the stacked widget based on the current
        value of a combo box selection widget in the given `form`.
        """

        box = form.get_value_widget(self._name)
        box.currentIndexChanged[QtCore.QString].connect(self._update_value)

    def update(self, form):
        box = form.get_value_widget(self._name)
        self._update_value(box.currentText())

    def _update_policy(self, policy):
        """
        Adjust the size of the stacked widget based on the given `policy`.
        """

        currentWidget = self.currentWidget()
        if currentWidget is not None:
            currentWidget.setSizePolicy(policy, policy)
            if isinstance(currentWidget, SettingsTableWidget):
                frame_width = currentWidget.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
                height = currentWidget.verticalHeader().length() + 2 * frame_width
                self.setMaximumHeight(height)
            else:
                self.setMaximumHeight(0)

            currentWidget.adjustSize()
            self.adjustSize()

    def _update_value(self, text):
        """
        Update the stacked widget with the settings based on the given `text`.

        The `text` must be a valid class name for the given stacked form.
        """

        name = str(text).replace(' ', '_').lower()
        component = "reconstruction_{}".format(name)

        # The stacked widget may no longer need the current size.
        self._update_policy(QtGui.QSizePolicy.Ignored)

        if component in self._forms:
            # The selected settings have been shown before, so only switch to 
            # it and update the size.
            self.setCurrentWidget(self._forms[component])
            self._update_policy(QtGui.QSizePolicy.Maximum)
            return

        # Retrieve a widget for the form.
        form = self._get_form(component)

        # Register the new form and show it in correct size.
        self._forms[component] = form
        index = self.addWidget(form)
        self.setCurrentIndex(index)
        self._update_policy(QtGui.QSizePolicy.Maximum)

    def _get_form(self, component):
        """
        Create a settings widget for a reconstructor.
        If the reconstructor class has a settings name `component` with
        the format "reconstruction_*", then a `SettingsTableWidget` is returned.
        Otherwise, an empty `QWidget` is returned.
        """

        try:
            self._arguments.get_settings(component)
        except KeyError:
            return QtGui.QWidget()
        else:
            return SettingsTableWidget(self._arguments, component)

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Reconstruction_View, self).__init__(controller, settings)

        self._running = False

        self._axes = None
        self._canvas = None
        self._image = None
        self._graph = None
        self._table = None

        self._sources = [
            {
                "title": "Dataset",
                "component": "reconstruction_dataset",
                "buffer": Dataset_Buffer
            },
            {
                "title": "Dump",
                "component": "reconstruction_dump",
                "buffer": Dump_Buffer
            },
            {
                "title": "Stream",
                "component": "reconstruction_stream",
                "buffer": Stream_Buffer
            }
        ]

        self._panels = None
        self._toggle_button = None
        self._snapshot_button = None

        self._source_forms = []

        self._pause_time = self._settings.get("reconstruction_pause_time") * 1000
        self._percentiles = None
        self._interpolation = None
        self._chunk_size = None
        self._cmap = None

        self._coordinator = None
        self._buffer = None
        self._stream_recorder = None
        self._reconstructor = None

        self._chunk_count = 0

        self._import_manager = Import_Manager()

        self._stacked_reconstructor = None
        self._stacked_model = None

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
        self._table = Table(self._settings)

        # Create the tab widget.
        tabs = QtGui.QTabWidget()
        tabs.addTab(self._graph.create(), "Graph")
        tabs.addTab(self._table.create(), "Table")

        # Create the panels. These are tabs containing the forms for each input 
        # source (dataset, dump and stream). Additionally, there are stacked 
        # widgets for the reconstructor-specific and model-specific settings.
        self._panels = QtGui.QTabWidget()
        self._panels.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)

        self._source_forms = []

        arguments = self._controller.arguments
        self._stacked_reconstructor = Stacked_Settings_Form(arguments,
                                                            "reconstructor_class")
        self._stacked_model = Stacked_Settings_Form(arguments, "model_class")

        for source in self._sources:
            form = SettingsTableWidget(arguments, source["component"])

            # Handle changes to the reconstructor and model class combo box 
            # selection widgets to show its settings in the respective stacked 
            # widget.
            self._stacked_reconstructor.register_form(form)
            self._stacked_model.register_form(form)

            # Register the source settings widget.
            self._panels.addTab(form, source["title"])
            self._source_forms.append(form)

        # Create the toggle button (using the stopped state as default).
        self._toggle_button = QtGui.QPushButton(QtGui.QIcon("assets/start.png"), "Start")
        self._toggle_button.clicked.connect(self._toggle)

        # Create the snapshot button.
        self._snapshot_button = QtGui.QPushButton(QtGui.QIcon("assets/snapshot.png"), "Snapshot")
        self._snapshot_button.clicked.connect(self._snapshot)

        # Create the layout and add the widgets.
        vbox_left_buttons = QtGui.QHBoxLayout()
        vbox_left_buttons.addWidget(self._toggle_button)
        vbox_left_buttons.addWidget(self._snapshot_button)

        vbox_left = QtGui.QVBoxLayout()
        vbox_left.addWidget(self._panels)
        vbox_left.addWidget(self._stacked_reconstructor)
        vbox_left.addWidget(self._stacked_model)
        vbox_left.addLayout(vbox_left_buttons)

        vbox_right = QtGui.QVBoxLayout()
        vbox_right.addWidget(self._canvas)
        vbox_right.addStretch(1)
        vbox_right.addWidget(tabs)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addLayout(vbox_left)
        hbox.addLayout(vbox_right)

        # Update the stacked widgets when switching tabs in the panel, and 
        # ensure the first stacked widget is loaded.
        self._panels.currentChanged.connect(self._update_form)
        self._update_form(0)

    def _toggle(self):
        """
        Toggle the state of the reconstruction (start or stop).
        """

        self._running = not self._running

        if self._running:
            self._toggle_button.setIcon(QtGui.QIcon("assets/stop.png"))
            self._toggle_button.setText("Stop")

            self._start()
        else:
            self._toggle_button.setIcon(QtGui.QIcon("assets/start.png"))
            self._toggle_button.setText("Start")

    def _snapshot(self):
        """
        Snapshot the current reconstructed image.
        """

        if self._running and self._image is not None:
            plt.imsave("snapshots/{}.pdf".format(datetime.datetime.now()), self._image, origin="lower")
        else:
            message = "Snapshotting is only possible when the reconstruction is started and an image is rendered."
            QtGui.QMessageBox.critical(self._controller.central_widget, "Snapshot error", message)

    def _update_form(self, index):
        """
        Update the stacked widget with the reconstructor settings based
        on the reconstructor combo box in the current source form.
        """

        form = self._source_forms[index]
        self._stacked_reconstructor.update(form)
        self._stacked_model.update(form)

    def _set_form_settings(self, form):
        """
        Retrieve and update settings from a settings form widget.

        If an error occurs, it is displayed and the method returns `None`
        instead of the `Settings` object.
        """

        settings = form.get_settings()
        try:
            values, disallowed = form.get_all_values()
            form.check_disallowed(disallowed)
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Invalid value", e.message)
            return None

        for key, value in values.iteritems():
            try:
                settings.set(key, value)
            except ValueError as e:
                QtGui.QMessageBox.critical(self._controller.central_widget,
                                           "Settings error", e.message)
                return None

        return settings

    def _start(self):
        """
        Start the reconstruction process.
        """

        # Determine the current panel and update the settings from the form.
        panel_id = self._panels.currentIndex()
        source = self._sources[panel_id]
        source_form = self._source_forms[panel_id]

        settings = self._set_form_settings(source_form)
        if settings is None:
            self._toggle()
            return

        # Update reconstructor and model settings, respectively, if ones that 
        # have settings are selected.
        for stacked_widget in (self._stacked_reconstructor, self._stacked_model):
            form = stacked_widget.currentWidget()
            if isinstance(form, SettingsTableWidget):
                form_settings = self._set_form_settings(form)
                if form_settings is None:
                    self._toggle()
                    return

        # Fetch the settings for the reconstruction.
        self._percentiles = settings.get("percentiles")
        self._interpolation = settings.get("interpolation")
        self._chunk_size = settings.get("chunk_size")

        # Prepare the color map for the reconstruction.
        cmap = plt.get_cmap(settings.get("cmap"))
        self._cmap = np.array([cmap(color) for color in range(256)]) * 255

        # Create the buffer and reconstructor.
        try:
            self._create_buffer(source, settings)
            self._create_reconstructor(settings)
        except IOError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "File error",
                                       "Could not open file '{}': {}".format(e.filename, e.strerror))
            self._toggle()
            return
        except StandardError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "Initialization error", e.message)
            self._toggle()
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
        self._image = None

        # Execute the reconstruction and visualization.
        self._chunk_count = 0
        self._loop()

    def _create_buffer(self, source, settings):
        """
        Create the buffer for the reconstruction process (depending on the data source).
        """

        buffer_class = source["buffer"]
        self._buffer = buffer_class(settings)

        if isinstance(self._buffer, Stream_Buffer):
            self._buffer.register_rf_sensor(self._controller.rf_sensor)

            if settings.get("stream_record") or settings.get("stream_calibrate"):
                # Create a stream recorder instance to record all incoming 
                # packets. The existence of this object is enough to let the 
                # loop handle the recording process.
                self._stream_recorder = Stream_Recorder(self._controller, settings)

    def _create_reconstructor(self, settings):
        """
        Create the reconstructor for the reconstruction process.
        """

        reconstructor = settings.get("reconstructor_class")
        reconstructor_class = self._import_manager.load_class(reconstructor,
                                                              relative_module="reconstruction")

        self._reconstructor = reconstructor_class(self._controller.arguments)

    def _loop(self):
        """
        Prepare the reconstruction loop by handling stopping and repeating.
        """

        # Stop if the stop button has been pressed.
        if not self._running:
            if self._stream_recorder is not None:
                self._stream_recorder.export()
                self._stream_recorder = None

            return

        self._execute()

        QtCore.QTimer.singleShot(self._pause_time, self._loop)

    def _execute(self):
        """
        Execute the reconstruction loop by handling incoming packets.
        """

        # If no packets are available yet, wait for them to arrive.
        if self._buffer.count() == 0:
            return

        try:
            packet, calibrated_rssi = self._buffer.get()
        except (TypeError, KeyError):
            # The buffer returned `None` or a calibration value is not
            # available, so ignore this packet.
            self._controller.thread_manager.log("control_panel_reconstruction_view")
            return

        # Update the graph, table and stream recorder (if applicable) with the packet.
        self._graph.update(packet)
        self._table.update(packet)
        if self._stream_recorder is not None:
            self._stream_recorder.update(packet)

        # Only use packets with valid source and destination locations.
        if not packet.get("from_valid") or not packet.get("to_valid"):
            return

        # Skip rendering when we are calibrating to reduce CPU usage and because
        # the rendered images are not meaningful.
        panel_id = self._panels.currentIndex()
        source_form = self._source_forms[panel_id]
        settings = source_form.get_settings()

        if isinstance(self._buffer, Stream_Buffer) and settings.get("stream_calibrate"):
            return

        # We attempt to reconstruct an image when the coordinator successfully
        # updated the weight matrix and the RSSI vector and when we have obtained
        # the required number of measurements to fill a chunk.
        if self._coordinator.update(packet, calibrated_rssi):
            self._chunk_count += 1
            if self._chunk_count >= self._chunk_size:
                self._chunk_count = 0

                thread.start_new_thread(self._render, ())

    def _render(self):
        """
        Render and draw the image using Matplotlib. This runs in a separate thread.
        """

        try:
            # Get the list of pixel values from the reconstructor.
            pixels = self._reconstructor.execute(self._coordinator.get_weight_matrix(),
                                                 self._coordinator.get_rssi_vector(),
                                                 buffer=self._buffer)

            # Reshape the list of pixel values to form the image. Smoothen the image
            # by suppressing pixel values that do not correspond to high attenuation.
            pixels = pixels.reshape(self._buffer.size)
            levels = [np.percentile(pixels, self._percentiles[0]), np.percentile(pixels, self._percentiles[1])]
            self._image = pg.functions.makeRGBA(pixels, levels=levels, lut=self._cmap)[0]

            # Draw the image onto the canvas and apply interpolation.
            self._axes.axis("off")
            self._axes.imshow(self._image, origin="lower", interpolation=self._interpolation)
            self._canvas.draw()

            # Delete the image from memory now that it is drawn.
            self._axes.cla()
        except StandardError:
            # There is not enough data yet for the reconstruction algorithm.
            pass
