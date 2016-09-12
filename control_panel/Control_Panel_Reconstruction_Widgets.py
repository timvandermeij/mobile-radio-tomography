# Core imports
import json
import os

# Library imports
import numpy as np
import pyqtgraph as pg
from PyQt4 import QtGui, QtCore

# Package imports
from Control_Panel_Settings_Widgets import SettingsTableWidget
from ..reconstruction.Buffer import Buffer

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

class Grid(QtGui.QGraphicsView):
    def __init__(self, settings=None, size=None):
        """
        Initialize the grid object.
        """

        super(Grid, self).__init__()

        if settings is not None and size is not None:
            raise TypeError("Either one of `settings` and `size` must be given, not both")

        if settings is not None:
            self._size = settings.get("reconstruction_grid_size")
        elif size is not None:
            self._size = size
        else:
            raise TypeError("Either one of `settings` and `size` must be given")

        self._clear = False

        self._links = []
        self._sensors = {}

        self._sensor_image = None

        # Create the scene.
        self._scene = QtGui.QGraphicsScene()
        self.setScene(self._scene)

    def setup(self, buffer):
        """
        Setup the grid.

        Retrieve the size from the `buffer`, which is either a `Buffer` object
        or a tuple or list containing the network width and height.
        """

        if isinstance(buffer, Buffer):
            self._width, self._height = buffer.size
        elif isinstance(buffer, (tuple, list)) and len(buffer) == 2:
            self._width, self._height = buffer
        else:
            raise TypeError("`buffer` must be a `Buffer` object or tuple of length 2")

        self._cell_size = self._size / max(self._width, self._height)

        sensor_image = QtGui.QPixmap("assets/network-wireless.png")
        self._sensor_image = sensor_image.scaledToHeight(self._cell_size)

        # Clear the scene for (re)drawing the grid.
        self._scene.clear()

        # Draw the grid.
        self._draw()

    def _draw(self):
        """
        Draw the grid onto the scene.
        """

        horizontal_coordinates = np.linspace(0, self._height * self._cell_size, self._height + 1)
        vertical_coordinates = np.linspace(0, self._width * self._cell_size, self._width + 1)
        horizontal_extend = min(max(vertical_coordinates), self._size)
        vertical_extend = min(max(horizontal_coordinates), self._size)

        for coordinate in horizontal_coordinates:
            self._scene.addLine(0, coordinate, horizontal_extend, coordinate,
                                QtGui.QPen(QtCore.Qt.black))

        for coordinate in vertical_coordinates:
            self._scene.addLine(coordinate, 0, coordinate, vertical_extend,
                                QtGui.QPen(QtCore.Qt.black))

    def _calculate_offset(self, position, center=False):
        centering = 0.5 * self._cell_size if center else 0.0
        x = position[1] * self._cell_size - centering
        y = (self._height - position[0]) * self._cell_size - centering

        return x, y

    def add_link(self, source, target):
        """
        Add a link to the scene. The link consists of two tuples
        indicating the `source` and `target` sensor locations.
        """

        # Remove existing links if necessary.
        if self._clear:
            self.clear()

        pen = QtGui.QPen(QtCore.Qt.blue, 2, QtCore.Qt.SolidLine)
        points = []

        for position in [source, target]:
            points.extend(self._calculate_offset(position))

        line = self._scene.addLine(*points, pen=pen)
        self._links.append(line)

    def add_sensor(self, sensor_id, position):
        if sensor_id not in self._sensors:
            self._sensors[sensor_id] = self._scene.addPixmap(self._sensor_image)

        x, y = self._calculate_offset(position, center=True)
        self._sensors[sensor_id].setOffset(x, y)

    def update(self, packet):
        """
        Update the grid with information in the `packet`, which is a `Packet`
        object containing information belonging to the `"rssi_ground_station"`
        specification.
        """

        # Determine the position coordinates.
        source = (packet.get("from_latitude"), packet.get("from_longitude"))
        target = (packet.get("to_latitude"), packet.get("to_longitude"))

        # Update the sensor location of the target sensor.
        self.add_sensor(packet.get("sensor_id"), target)

        # Add the new link if the locations are valid.
        if not packet.get("from_valid") or not packet.get("to_valid"):
            return

        self.add_link(source, target)

    def toggle(self, state):
        """
        Toggle whether or not we should clear previous links before
        adding a new one to the scene. The `state` indicates if the
        checkbox in the view has been checked, in which case we must
        clear the links everytime before adding a new one.
        """

        self._clear = (state == QtCore.Qt.Checked)

    def clear(self):
        """
        Clear the grid. We remove all links, but the grid lines and the sensor
        positions remain.
        """

        for link in self._links:
            self._scene.removeItem(link)

        self._links = []

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
