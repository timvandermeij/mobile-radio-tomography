# Core imports
import datetime
import thread

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
from Control_Panel_Reconstruction_Widgets import Graph, Grid, Table, Stream_Recorder, Stacked_Settings_Form
from Control_Panel_Settings_Widgets import SettingsTableWidget
from Control_Panel_View import Control_Panel_View
from ..core.Import_Manager import Import_Manager
from ..reconstruction.Coordinator import Coordinator
from ..reconstruction.Dataset_Buffer import Dataset_Buffer
from ..reconstruction.Dump_Buffer import Dump_Buffer
from ..reconstruction.Stream_Buffer import Stream_Buffer

class Control_Panel_Reconstruction_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Reconstruction_View, self).__init__(controller, settings)

        self._running = False

        self._axes = None
        self._canvas = None
        self._image = None

        self._graph = None
        self._grid = None
        self._grid_checkbox = None
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

        # Create the tabs (and corresponding widgets).
        top_tabs, bottom_tabs = self._create_tabs()

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
        vbox_right.addWidget(top_tabs, 2)
        vbox_right.addWidget(bottom_tabs, 1)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addLayout(vbox_left)
        hbox.addLayout(vbox_right)

        # Update the stacked widgets when switching tabs in the panel, and 
        # ensure the first stacked widget is loaded.
        self._panels.currentChanged.connect(self._update_form)
        self._update_form(0)

    def _create_tabs(self):
        """
        Create widgets (graph, grid and table) for the view and return
        the tabs that contain them.
        """

        # Create the grid.
        self._grid = Grid(self._settings)
        self._grid_checkbox = QtGui.QCheckBox("Only show current measurement")
        self._grid_checkbox.stateChanged.connect(self._grid.toggle)

        grid_layout = QtGui.QVBoxLayout()
        grid_layout.addWidget(self._grid_checkbox)
        grid_layout.addWidget(self._grid)
        grid_widget = QtGui.QWidget()
        grid_widget.setLayout(grid_layout)

        # Create the graph and table.
        self._graph = Graph(self._settings)
        self._table = Table(self._settings)

        # Create the top tabs.
        top_tabs = QtGui.QTabWidget()
        top_tabs.addTab(self._canvas, "Image")
        top_tabs.addTab(grid_widget, "Grid")

        # Create the bottom tabs.
        bottom_tabs = QtGui.QTabWidget()
        bottom_tabs.addTab(self._graph.create(), "Graph")
        bottom_tabs.addTab(self._table.create(), "Table")

        return top_tabs, bottom_tabs

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

        # Clear the widgets.
        self._graph.clear()
        self._graph.setup(self._buffer)
        self._table.clear()
        self._grid.clear()
        self._grid.setup(self._buffer)

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

        # Update the widgets with the packet.
        self._graph.update(packet)
        self._grid.update(packet)
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
            image = pg.functions.makeRGBA(pixels, levels=levels, lut=self._cmap)[0]

            # Ignore empty images. This may happen after applying the levels
            # when not enough data is present yet.
            if len(np.unique(image)) == 1:
                return

            # Draw the image onto the canvas and apply interpolation.
            self._axes.axis("off")
            self._axes.imshow(image, origin="lower", interpolation=self._interpolation)
            self._canvas.draw()
            self._image = image

            # Delete the image from memory now that it is drawn.
            self._axes.cla()
        except StandardError:
            # There is not enough data yet for the reconstruction algorithm.
            pass
