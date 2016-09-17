import json
import os
from collections import OrderedDict
from functools import partial
from PyQt4 import QtGui
from Control_Panel_RF_Sensor_Sender import Control_Panel_RF_Sensor_Sender
from Control_Panel_Settings_Widgets import SettingsTableWidget
from Control_Panel_View import Control_Panel_View
from Control_Panel_Waypoints_Widgets import WaypointsTableWidget, WaypointTypeWidget, WaypointsTableValueError
from ..geometry.Geometry import Geometry
from ..planning.Greedy_Assignment import Greedy_Assignment
from ..waypoint.Waypoint import Waypoint_Type
from ..zigbee.Packet import Packet

class Control_Panel_Waypoints_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Waypoints_View, self).__init__(controller, settings)

        self._max_retries = self._settings.get("waypoints_max_retries")
        self._retry_interval = self._settings.get("waypoints_retry_interval")

        self._vehicle_labels = []
        self._tables = []

        # Columns in the table widgets. The columns are ordered, and each 
        # column has the following properties:
        # - "field": The internal name of the column.
        # - "label": The label in the table widget's horizontal (top) header.
        # - "default": The default value when nothing is inserted in the cell
        #   of some row. When this is `None`, then the column is required, but
        #   will inherit values from previous rows. The latter is also the case
        #   for other values that evaluate to `False`, but fall back to the 
        #   default if no previous data is available. Other defaults are always 
        #   used as the value if the cell is not filled. The defaults play 
        #   a large role whenever we import, export or otherwise process the 
        #   table data.
        # Additionally, the columns may have the following properties:
        # - "widget": A cell widget type to fill in the rows. The given type
        #   must be a subclass of `QtWidget`, and it must implement two 
        #   methods: `get_value` and `set_value(data)`.
        # - "min": The minimum numeric value for the cell. The cell is
        #   considered invalid if its data value is lower than the minimum.
        # - "offset": The displayed numeric value is this much higher than the
        #   value that we store and send internally.
        self._columns = [
            {
                "field": "north",
                "label": "north",
                "default": None
            },
            {
                "field": "east",
                "label": "east",
                "default": None
            },
            {
                "field": "alt",
                "label": "altitude",
                "default": 0.0
            },
            {
                "field": "type",
                "label": "type",
                "default": int(Waypoint_Type.WAIT),
                "widget": WaypointTypeWidget
            },
            {
                "field": "wait_id",
                "label": "wait for vehicle",
                "default": 0,
                "min": 0
            },
            {
                "field": "wait_count",
                "label": "wait count",
                "default": 1,
                "min": 1
            },
            {
                "field": "wait_waypoint",
                "label": "wait for waypoint",
                "default": -1,
                "min": -1,
                "offset": 1
            }
        ]

        self._column_defaults = tuple(
            column["default"] for column in self._columns
        )

        # Internal field names that can be used for indexing.
        self._fields = OrderedDict([
            (column["field"], i) for i, column in enumerate(self._columns)
        ])

        self._listWidget = None
        self._stackedLayout = None
        self._reassign_checkbox = None

        self._geometry = Geometry()

    def load(self, data):
        self._listWidget = QtGui.QListWidget()
        self._stackedLayout = QtGui.QStackedLayout()

        for vehicle in xrange(1, self._controller.rf_sensor.number_of_sensors + 1):
            # Create the list item for the vehicle.
            self._listWidget.addItem("Waypoints for vehicle {}".format(vehicle))

            # Create the table for the vehicle.
            table = WaypointsTableWidget(self._columns, vehicle)
            table.menuRequested.connect(partial(self._fill_menu, vehicle))

            self._tables.append(table)
            self._stackedLayout.addWidget(table)

        if "waypoints" in data:
            try:
                waypoints = self._convert_waypoints(data["waypoints"])
                self._import_waypoints(waypoints, from_json=False)
            except ValueError:
                return

    def save(self):
        return {
            "waypoints": self._export_waypoints(repeat=False, errors=False)[0]
        }

    def show(self):
        """
        Show the waypoints view.
        """

        self._add_menu_bar()

        self._listWidget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        self._listWidget.setCurrentRow(0)
        self._listWidget.currentRowChanged.connect(self._stackedLayout.setCurrentIndex)

        # Create the buttons for adding new rows and sending the waypoints.
        add_row_button = QtGui.QPushButton("Add row")
        add_row_button.clicked.connect(self._add_row)
        self._reassign_checkbox = QtGui.QCheckBox("Reassign")
        self._reassign_checkbox.toggled.connect(self._reassign_settings)
        import_button = QtGui.QPushButton("Import")
        import_button.clicked.connect(self._import)
        export_button = QtGui.QPushButton("Export")
        export_button.clicked.connect(self._export)
        compress_button = QtGui.QPushButton("Compress")
        compress_button.clicked.connect(self._compress)
        uncompress_button = QtGui.QPushButton("Uncompress")
        uncompress_button.clicked.connect(self._uncompress)
        send_button = QtGui.QPushButton("Send")
        send_button.clicked.connect(self._send)

        # Create the layout and add the widgets.
        hbox_stacks = QtGui.QHBoxLayout()
        hbox_stacks.addWidget(self._listWidget)
        hbox_stacks.addLayout(self._stackedLayout)

        hbox_buttons = QtGui.QHBoxLayout()
        hbox_buttons.addWidget(add_row_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(self._reassign_checkbox)
        hbox_buttons.addWidget(import_button)
        hbox_buttons.addWidget(export_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(compress_button)
        hbox_buttons.addWidget(uncompress_button)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(send_button)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox_stacks)
        vbox.addLayout(hbox_buttons)

    def _add_row(self):
        """
        Add a row to all tables at the same time.
        """

        for table in self._tables:
            table.insertRow(table.rowCount())

    def _format_row_data(self, vehicle, table, row, previous, repeat=True,
                         errors=True):
        """
        Format a single row from a waypoints table for exporting.

        This method grabs the cells from the given `table` at row number `row`
        for the given vehicle `vehicle`, given that the data from the previous
        row is given in `previous`. If there is no previous row, then this is
        equal to the column defaults.

        Returns the list of formatted data with appropriate types and values,
        or an empty list if the row is completely empty with no previous rows.

        Can raise a `ValueError` for missing or invalid cell data.
        """

        data, empty = table.get_row_data(row)

        if empty and previous == self._column_defaults:
            # If this is the first table row or all previous rows are empty, 
            # and this row is (also) completely empty, i.e., no cells were 
            # filled or altered, then silently ignore this row.
            return []

        if errors:
            pairs = zip(range(len(self._columns)), data, previous)
            bad_columns = [
                col for col, val, prev in pairs if val is None and prev is None
            ]
            if bad_columns:
                # If a column has no data and no previous data either, then we 
                # have missing information.
                raise WaypointsTableValueError("Missing coordinates for vehicle {}, row #{} and no previous waypoint".format(vehicle, row + 1), vehicle, row, bad_columns)

        for i, column in enumerate(self._columns):
            if data[i] is None:
                # If a table cell is empty, then either use the previous 
                # waypoint's coordinates for the current waypoint if `repeat` 
                # is enabled and the column default is a value which evaluates 
                # to `False`. Otherwise, we just use the column default. For 
                # example, "wait_count" and "wait_waypoint" never repeat data 
                # from earlier rows, since their default is either more basic 
                # or more intricate than just repeating the previous value.
                if repeat and not column["default"]:
                    data[i] = previous[i]
                else:
                    data[i] = column["default"]
            else:
                try:
                    data[i] = table.cast_cell(row, i, data[i])
                except ValueError:
                    if errors:
                        raise WaypointsTableValueError("Invalid value for vehicle {}, row #{}, column '{}': '{}'".format(vehicle, row + 1, column["label"], data[i]), vehicle, row, i)

            if errors and "min" in column and data[i] < column["min"]:
                raise WaypointsTableValueError("Invalid value for vehicle {}, row #{}, column '{}': {} must be at least {}".format(vehicle, row + 1, column["label"], data[i], column["min"]), vehicle, row, i)

        if errors and row > 0 and data[self._fields["type"]] == Waypoint_Type.HOME:
            raise WaypointsTableValueError("Waypoint type for vehicle {}, row #{} may not be 'home'.".format(vehicle, row + 1), vehicle, row, self._fields["type"])

        return data

    def _get_wait_id(self, vehicle, waypoint):
        """
        Retrieve the vehicle sensor ID to wait for at a specific waypoint.

        The given `vehicle` is the sensor ID of the vehicle that will receive
        the waypoint. `waypoint` is a list of formatted row data. If it contains
        a wait ID, then it is returned. If the wait ID is the default, i.e.,
        synchronize with all vehicles if synchronization is enabled, and there
        are only two vehicles, then return the ID of the other sensor.
        Otherwise, `0` is returned.
        """

        default = self._columns[self._fields["wait_id"]]["default"]
        if waypoint[self._fields["type"]] != Waypoint_Type.WAIT:
            return default

        wait_id = waypoint[self._fields["wait_id"]]
        number_of_sensors = self._controller.rf_sensor.number_of_sensors
        if number_of_sensors == 2:
            if wait_id == default:
                # Vehicle IDs are indexed from 1, so with two vehicles, the 
                # wait ID for vehicle 1 is vehicle 2 and vice versa.
                return vehicle % number_of_sensors + 1

        return wait_id

    def _get_wait_waypoint(self, waypoints, index):
        """
        Retrieve the other vehicle's wait waypoint ID to wait for at a given
        waypoint.

        Wait waypoint IDs do not match up with the waypoint indexes, but instead
        only count the wait waypoints.

        The given `waypoints` is a list of lists containing formatted table data
        for the current vehicle, and `index` is the index of the waypoint.
        formatted row data. If it contains a wait waypoint index, then it is
        returned. If the wait waypoint is the default, then return the current
        waypoint index.
        """

        default = self._columns[self._fields["wait_waypoint"]]["default"]
        if waypoints[index][self._fields["type"]] != Waypoint_Type.WAIT:
            return default

        wait_waypoint = waypoints[index][self._fields["wait_waypoint"]]
        if wait_waypoint == default:
            return self._count_wait_waypoints(waypoints, index=index)

        return wait_waypoint

    def _count_wait_waypoints(self, waypoints, index=None):
        """
        Count the number of waypoints of the type "wait" for some vehicle.

        The given `waypoints` is a list of lists containing formatted table data
        for the current vehicle. If given, `index` specifies the waypoint index
        to count up to (but excluding that waypoint).
        """

        type_col = self._fields["type"]
        return sum(
            row[type_col] == Waypoint_Type.WAIT for row in waypoints[:index]
        )

    def _make_location(self, waypoint):
        """
        Convert a formatted waypoint list `waypoint` into a `Location` object.

        Returns the `LocationLocal` object.
        """

        return self._geometry.make_location(*waypoint[0:3])

    def _uncompress_waypoint(self, data, row):
        """
        Given a list of formatted waypoint dictionaries `data`, convert the
        waypoint row `row` into a full range of waypoints.

        If the waypoint data has a "wait_count" greater than one, then the
        waypoint is transformed into a range between the previous waypoint and
        the current waypoint. If there is no previous waypoint, then we assume
        that the we wait "wait_count" number of times at the current waypoint.

        Returns the list of resulting `LocationLocal` objects, with the same
        length as the "wait_count".
        """

        count = data[row][self._fields["wait_count"]]
        current_loc = self._make_location(data[row])
        if row < 1:
            return [current_loc] * count

        previous_loc = self._make_location(data[row-1])
        return self._geometry.get_location_range(previous_loc, current_loc,
                                                 count=count)

    def _compress_waypoints(self, vehicle, data):
        """
        Compress the given formatted list of waypoints `data` that was retrieved
        from the table for the given vehicle ID `vehicle`.

        This method attempts to find subsequent waypoints that match with
        a range generated from the previous waypoint and the last waypoint in
        the sequence found. The longest sequence is matched and replaced with
        a single waypoint that holds a "wait_count" to generate the same range.

        Waypoints that are already "compressed" are accounted for, i.e., they
        are uncompressed using their wait count during the range matching.

        The first and last waypoints of the table are mostly retained. The first
        waypoint needs to be retained because we either do not know how to
        generate it from a range starting from the home location which is not
        available at this point, or the waypoint describes the home location.
        However, if the second waypoint is the same as the first (and so on),
        then these are compressed into one waypoint with correct "wait_count".
        The last waypoint cannot be the start of a range, although it can be
        the end of a compressed range, in which case its wait count is updated.
        """

        row = 0
        while row < len(data) - 1:
            # The "previous" location upon which we may be able to create 
            # a range of subsequent waypoints.
            start_location = self._make_location(data[max(0, row-1)])

            # The wait ID of the first waypoint in the sequence of waypoints.
            wait_id = self._get_wait_id(vehicle, data[row])

            # The wait waypoint index of the first waypoint in the sequence.
            wait_waypoint = self._get_wait_waypoint(data, row)

            # The last row number that is a part of the range thus far.
            end = row

            # The range of locations from the sequence of waypoints thus far.
            L = self._uncompress_waypoint(data, row)

            # The length of the range of locations thus far, which could become 
            # the "wait_count" of the compressed range.
            wait_count = len(L)
            for range_row in range(row + 1, len(data)):
                # If the waypoint type is not "wait", then it is not a part of 
                # the range.
                if data[range_row][self._fields["type"]] != Waypoint_Type.WAIT:
                    break

                # If the next row has a different vehicle wait ID, then the 
                # range ends before it.
                if wait_id != self._get_wait_id(vehicle, data[range_row]):
                    break

                # If the next row has a wait waypoint index that is one more 
                # than the previous, then the range ends before it.
                range_wait_waypoint = self._get_wait_waypoint(data, range_row)
                if wait_waypoint + range_row - row != range_wait_waypoint:
                    break

                # Add the locations of the next waypoint to the range, so that 
                # we can determine whether we can create this range using just 
                # one waypoint.
                L.extend(self._uncompress_waypoint(data, range_row))

                # If we start at the first waypoint, then only check whether 
                # all locations are equal to the this location. If so, then we 
                # can safely compress it into that waypoint. Otherwise, a range 
                # has no starting location, so we cannot make different ranges.
                if row == 0:
                    if all(self._geometry.equals(start_location, a) for a in L):
                        end = range_row
                        wait_count = len(L)
                        continue

                    break

                # Create the range of locations that would be generated if we 
                # only had the last waypoint, and the previous one before the 
                # range started.
                R = self._geometry.get_location_range(start_location, L[-1],
                                                      count=len(L))

                # Check if the current "explicit" range is the same as 
                # generated range. If it is, then the generated range is still 
                # valid and we could replace those waypoints with only one.
                if any(not self._geometry.equals(a, b) for a, b in zip(L, R)):
                    break

                end = range_row
                wait_count = len(L)

            if end != row:
                # We found a range with more than one waypoint, so replace it 
                # with the last waypoint in the range. Update its "wait_count" 
                # based on the length of the actual range, and keep the first
                # "wait_waypoint" encountered in the range.
                new_waypoint = list(data[end])
                new_waypoint[self._fields["wait_count"]] = wait_count
                new_waypoint[self._fields["wait_waypoint"]] = wait_waypoint
                data[row:end+1] = [tuple(new_waypoint)]

            row += 1

    def _uncompress_waypoints(self, vehicle, data):
        """
        Uncompress the given formatted list of waypoints `data` that was
        retrieved from the table for the given vehicle ID `vehicle`.

        This replaces each waypoint that has a "wait_count" with the
        corresponding range of locations from the previous waypoint to that
        waypoint. It also fills default "wait_id" fields if we only have two
        sensor vehicles.
        """

        row = 0
        while row < len(data):
            locations = self._uncompress_waypoint(data, row)
            wait_id = self._get_wait_id(vehicle, data[row])
            wait_waypoint = self._get_wait_waypoint(row, data[row])

            waypoints = []
            for i, loc in enumerate(locations):
                fields = {
                    "north": loc.north,
                    "east": loc.east,
                    "alt": -loc.down,
                    "wait_id": wait_id,
                    "wait_count": 1,
                    "wait_waypoint": wait_waypoint + i
                }
                waypoint = []
                for col, column in enumerate(self._columns):
                    if column["field"] in fields:
                        waypoint.append(fields[column["field"]])
                    else:
                        waypoint.append(data[row][col])

                waypoints.append(waypoint)

            data[row:row+1] = waypoints
            row += len(locations)

    def _validate_waypoints(self, waypoints):
        """
        Validate an assignment of `waypoints` for consistency checks.

        The given `waypoints` is a dictionary, with vehicle sensor IDs as keys
        and lists of formatted waypoint lists as values.

        Any consistency failures raise a `ValueError`.
        """

        for vehicle, rows in waypoints.iteritems():
            wait_count = 0
            for row, waypoint in enumerate(rows):
                if waypoint[self._fields["type"]] == Waypoint_Type.WAIT:
                    wait_id = self._get_wait_id(vehicle, waypoint)
                    wait_waypoint = waypoint[self._fields["wait_waypoint"]]
                    if wait_id > 0 and wait_id != vehicle and wait_waypoint != -1:
                        self._validate_wait_waypoint(waypoints, vehicle, row,
                                                     wait_count, wait_id,
                                                     wait_waypoint)

                    wait_count += 1

    def _validate_wait_waypoint(self, waypoints, vehicle, row, wait_count,
                                wait_id, wait_waypoint):
        type_col = self._fields["type"]
        wait_waypoint_col = self._fields["wait_waypoint"]

        if wait_id not in waypoints:
            raise WaypointsTableValueError("Waypoint for vehicle {}, row #{} references vehicle {} which has no waypoints".format(vehicle, row+1, wait_id), vehicle, row, self._fields["wait_id"])

        wait_waypoints = [
            data for data in waypoints[wait_id]
            if data[type_col] == Waypoint_Type.WAIT
        ]
        if wait_waypoint >= len(wait_waypoints):
            raise WaypointsTableValueError("Waypoint for vehicle {}, row #{} references nonexistent wait waypoint {} from vehicle {}".format(vehicle, row+1, wait_waypoint, wait_id), vehicle, row, wait_waypoint_col)

        other_id = self._get_wait_id(wait_id, wait_waypoints[wait_waypoint])
        if other_id != vehicle:
            raise WaypointsTableValueError("Waypoint for vehicle {}, row #{} references wrong wait waypoint {} from vehicle {}; the latter has wait id {}".format(vehicle, row+1, wait_waypoint, wait_id, other_id), vehicle, row, wait_waypoint_col)

        other_count = wait_waypoints[wait_waypoint][wait_waypoint_col]
        if other_count == -1:
            other_count = wait_waypoint

        if other_count != wait_count:
            raise WaypointsTableValueError("Waypoint for vehicle {}, row #{} references wrong wait waypoint {} from vehicle {}; the latter points to wait waypoint {} instead of back to {}".format(vehicle, row+1, wait_waypoint, wait_id, other_count+1, wait_count+1), vehicle, row, wait_waypoint_col)

        for data in wait_waypoints[:wait_waypoint]:
            other_id = self._get_wait_id(wait_id, data)
            if other_id == vehicle and data[wait_waypoint_col] > wait_count:
                raise WaypointsTableValueError("Waypoint for vehicle {}, row #{} references wrong wait waypoint {} from vehicle {}; earlier wait waypoint references a later waypoint of this vehicle, leading to deadlocks".format(vehicle, row+1, wait_waypoint, wait_id), vehicle, row, wait_waypoint_col)

    def _export_waypoints(self, repeat=True, errors=True):
        """
        Create a dictonary containing lists of waypoints (tuples) per vehicle
        from the current contents of the tables.

        When `repeat` is enabled, the output for rows with empty column is
        augmented with data from previous rows. This is perfect for exporting
        to somewhat readable JSON files and the actual sending mechanisms, but
        can be disabled for internal storage since `_import_waypoint` handles
        data that is default differently than repeated data.

        When `errors` is enabled, columns that have missing first data when
        they are required raise a `ValueError`, and invalid values do as well.
        This can also be disabled for internal storage.
        """

        waypoints = {}
        total = 0
        for index, table in enumerate(self._tables):
            # Keep vehicle index as string here since send and save make use of 
            # integer indices, while JSON export will automatically convert 
            # them to string keys.
            vehicle = index + 1
            previous = self._column_defaults
            for row in range(table.rowCount()):
                data = self._format_row_data(vehicle, table, row, previous,
                                             repeat=repeat, errors=errors)

                if not data:
                    continue

                if vehicle not in waypoints:
                    waypoints[vehicle] = [tuple(data)]
                else:
                    waypoints[vehicle].append(tuple(data))

                total += 1
                previous = tuple(data)

        if errors:
            self._validate_waypoints(waypoints)

        return waypoints, total

    def _convert_waypoints(self, waypoints, reassign=False):
        """
        Convert an imported object containing waypoints to a dictionary of lists
        of waypoints (tuples) for each vehicle.

        If the `waypoints` objects is already such a dictionary, it is left
        intact. If it is a list, then it is assumed that it has lists of sensor
        pairs (lists of lists). This is mostly for compatibility with output
        from a planning algorithm. If `reassign` is `True`, then the list of
        sensor pairs is passed through the greedy assignment and the collision
        avoidance (if enabled) algorithms to generate an assignment that visits
        closer sensor links first.

        If the waypoints could not be converted, then a `ValueError` is raised.
        """

        if isinstance(waypoints, list):
            try:
                if reassign:
                    assigner = Greedy_Assignment(self._controller.arguments,
                                                 self._geometry)
                    waypoints, distance = assigner.assign(waypoints)
                    if distance == float('inf'):
                        raise ValueError("Given waypoints could not be reassigned because a collision was detected")
                else:
                    waypoints = {
                        "1": [sensor_pairs[0] for sensor_pairs in waypoints],
                        "2": [sensor_pairs[1] for sensor_pairs in waypoints]
                    }
            except IndexError:
                raise ValueError("JSON list must contain sensor pairs")
        elif not isinstance(waypoints, dict):
            raise ValueError("Waypoints must be a JSON list or array")

        return waypoints

    def _show_waypoint_error(self, e):
        """
        Display an error message related to an invalid waypoint from the
        `Exception` object `e`.

        If `e` is a `WaypointsTableValueError`, then the relevant cell or cells
        are marked invalid.
        """

        if isinstance(e, WaypointsTableValueError):
            if e.vehicle is not None and e.row is not None:
                if e.column is None:
                    columns = range(len(self._columns))
                elif isinstance(e.column, int):
                    columns = [e.column]
                else:
                    columns = list(e.column)

                self._listWidget.setCurrentRow(e.vehicle - 1)
                self._tables[e.vehicle-1].setCurrentCell(e.row, columns[0])

                for column in columns:
                    self._tables[e.vehicle-1].set_valid(e.row, column, False)

        QtGui.QMessageBox.critical(self._controller.central_widget,
                                   "Waypoint incorrect", e.message)

    def _import_waypoints(self, waypoints, from_json=True):
        """
        Populate the tables from a dictionary of lists of waypoints (tuples)
        for each vehicle.

        When `from_json` is enabled, consider the dictionary to be loaded from
        a JSON file, which has strings as vehicle index keys.
        """

        for index, table in enumerate(self._tables):
            # Allow either string or numeric indices depending on import source
            vehicle = str(index + 1) if from_json else index + 1
            if vehicle not in waypoints:
                continue

            table.removeRows()
            for row, waypoint in enumerate(waypoints[vehicle]):
                # Backward compatibility for JSON files without a type field.
                if from_json and len(waypoint) == len(self._columns) - 2:
                    field = self._fields["type"]
                    waypoint[field:field] = [self._columns[field]["default"]]

                table.insert_data_row(row, waypoint)

    def _reassign_settings(self, checked):
        if not checked:
            return

        forms = {}
        components = ("planning_assignment", "planning_collision_avoidance")
        hbox = QtGui.QHBoxLayout()
        for component in components:
            form = SettingsTableWidget(self._controller.arguments, component,
                                       include_parent=True)
            forms[component] = form

            vbox = QtGui.QVBoxLayout()
            vbox.addWidget(form)

            group = QtGui.QGroupBox(form.get_title())
            group.setLayout(vbox)

            hbox.addWidget(group)

        dialog = QtGui.QDialog(self._controller.central_widget)
        dialog.setWindowTitle("Change assignment settings")

        dialogButtons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        dialogButtons.accepted.connect(dialog.accept)
        dialogButtons.rejected.connect(dialog.reject)

        dialogLayout = QtGui.QVBoxLayout()
        dialogLayout.addLayout(hbox)
        dialogLayout.addWidget(dialogButtons)

        dialog.setLayout(dialogLayout)

        # Show the dialog and handle the input.
        result = dialog.exec_()
        if result != QtGui.QDialog.Accepted:
            return

        # Update the settings from the dialog forms.
        for component, form in forms.iteritems():
            settings = self._controller.arguments.get_settings(component)
            try:
                values, disallowed = form.get_all_values()
                form.check_disallowed(disallowed)
            except ValueError as e:
                QtGui.QMessageBox.critical(self._controller.central_widget,
                                           "Invalid value", e.message)
                return

            for key, value in values.iteritems():
                try:
                    settings.set(key, value)
                except ValueError as e:
                    QtGui.QMessageBox.critical(self._controller.central_widget,
                                               "Settings error", e.message)
                    return

    def _import(self):
        """
        Import waypoints from a JSON file that was exported from the waypoints
        view or from the planning algorithm.
        """

        fn = QtGui.QFileDialog.getOpenFileName(self._controller.central_widget,
                                               "Import file", os.getcwd(),
                                               "JSON files (*.json)")
        if fn == "":
            return

        reassign = self._reassign_checkbox.isChecked()

        try:
            with open(fn, 'r') as import_file:
                data = json.load(import_file)

            waypoints = self._convert_waypoints(data, reassign)
        except IOError as e:
            message = "Could not open file '{}': {}".format(fn, e.strerror)
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "File error", message)
            return
        except ValueError as e:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "JSON error", e.message)
            return

        try:
            self._import_waypoints(waypoints, from_json=not reassign)
        except ValueError as e:
            self._show_waypoint_error(e)

    def _export(self):
        """
        Export the waypoints in the tables to a JSON file.
        """

        try:
            waypoints = self._export_waypoints()[0]
        except ValueError as e:
            self._show_waypoint_error(e)
            return

        fn = QtGui.QFileDialog.getSaveFileName(self._controller.central_widget,
                                               "Export file", os.getcwd(),
                                               "JSON files (*.json)")
        if fn == "":
            return

        try:
            with open(fn, 'w') as export_file:
                json.dump(waypoints, export_file)
        except IOError as e:
            message = "Could not open file '{}': {}".format(fn, e.strerror)
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "File error", message)

    def _compress(self):
        """
        Compress the waypoints in the tables in any way possible.
        """

        try:
            waypoints = self._export_waypoints()[0]
        except ValueError as e:
            self._show_waypoint_error(e)
            return

        for vehicle, data in waypoints.iteritems():
            self._compress_waypoints(vehicle, data)

        try:
            self._import_waypoints(waypoints, from_json=False)
        except ValueError as e:
            self._show_waypoint_error(e)

    def _uncompress(self):
        """
        Inflate the waypoints in the tables in every way possible.
        """

        try:
            waypoints = self._export_waypoints()[0]
        except ValueError as e:
            self._show_waypoint_error(e)
            return

        for vehicle, data in waypoints.iteritems():
            self._uncompress_waypoints(vehicle, data)

        try:
            self._import_waypoints(waypoints, from_json=False)
        except ValueError as e:
            self._show_waypoint_error(e)

    def _send(self):
        """
        Send the waypoints from all tables to the corresponding vehicles.
        """

        try:
            waypoints, total = self._export_waypoints()
        except ValueError as e:
            self._show_waypoint_error(e)
            return

        if total == 0:
            QtGui.QMessageBox.critical(self._controller.central_widget,
                                       "No waypoints",
                                       "There are no vehicles with waypoints.")
            return

        configuration = {
            "name": "waypoint",
            "clear_message": "waypoint_clear",
            "add_callback": self._make_add_waypoint_packet,
            "done_message": "waypoint_done",
            "ack_message": "waypoint_ack",
            "max_retries": self._max_retries,
            "retry_interval": self._retry_interval
        }
        sender = Control_Panel_RF_Sensor_Sender(self._controller, waypoints,
                                                total, configuration)
        sender.start()

    def _make_add_waypoint_packet(self, vehicle, index, waypoint):
        """
        Create a `Packet` object with the `waypoint_add` specification
        and fill its fields with correct values.

        This is a callback for the `Control_Panel_RF_Sensor_Sender`.
        """

        packet = Packet()
        packet.set("specification", "waypoint_add")
        packet.set("latitude", waypoint[self._fields["north"]])
        packet.set("longitude", waypoint[self._fields["east"]])
        packet.set("altitude", waypoint[self._fields["alt"]])
        packet.set("type", waypoint[self._fields["type"]])
        packet.set("wait_id", waypoint[self._fields["wait_id"]])
        packet.set("wait_count", waypoint[self._fields["wait_count"]])
        packet.set("wait_waypoint", waypoint[self._fields["wait_waypoint"]])
        packet.set("index", index)
        packet.set("to_id", vehicle)

        return packet

    def _fill_menu(self, vehicle, actions, position):
        table = self._tables[vehicle-1]
        item = table.indexAt(position)
        row = item.row()
        enabled = item.isValid()

        if enabled:
            type_widget = table.cellWidget(row, self._fields["type"])
            if type_widget.get_value() != Waypoint_Type.WAIT:
                enabled = False

        goto_action = QtGui.QAction("Find referenced wait waypoint", table)
        goto_action.setEnabled(enabled)
        goto_action.triggered.connect(partial(self._goto_wait_waypoint, vehicle, row))

        actions.append(goto_action)

    def _goto_wait_waypoint(self, vehicle, row):
        waypoints = self._export_waypoints(repeat=False, errors=False)[0]

        if vehicle not in waypoints:
            return

        wait_id = self._get_wait_id(vehicle, waypoints[vehicle][row])
        wait_waypoint = self._get_wait_waypoint(waypoints[vehicle], row)

        if wait_id == 0 or wait_id not in waypoints or wait_waypoint == -1:
            return

        type_col = self._fields["type"]
        wait_waypoints = [
            index for index, data in enumerate(waypoints[wait_id])
            if data[type_col] == Waypoint_Type.WAIT
        ]

        if wait_waypoint >= len(wait_waypoints):
            return

        self._listWidget.setCurrentRow(wait_id - 1)
        self._tables[wait_id-1].setCurrentCell(wait_waypoints[wait_waypoint],
                                               self._fields["wait_waypoint"])
