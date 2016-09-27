from functools import partial
from PyQt4 import QtCore, QtGui
from ..location.Line_Follower import Line_Follower_Direction
from ..waypoint.Waypoint import Waypoint_Type

class WaypointsTableValueError(ValueError):
    """
    An exception caused by an invalid value in a cell of a waypoints table.
    """

    def __init__(self, message, vehicle=None, row=None, column=None):
        super(WaypointsTableValueError, self).__init__(message)
        self._vehicle = vehicle
        self._row = row
        self._column = column

    @property
    def vehicle(self):
        return self._vehicle

    @property
    def row(self):
        return self._row

    @property
    def column(self):
        return self._column

class WaypointEnumWidget(QtGui.QComboBox):
    def __init__(self, table, item, enum, default, label="{} ({})", *a, **kw):
        super(WaypointEnumWidget, self).__init__(*a, **kw)

        self._table = table
        self._item = item

        # Retrieve the existing members of the enum class. Use their name and 
        # value to populate the combo box options.
        self.addItems([
            label.format(member.value, member.name.lower())
            for member in iter(enum)
        ])

        self.setCurrentIndex(default - 1)

    def get_value(self):
        """
        Retrieve the current waypoint type value.

        The value is returned as an integer, assuming the enum class has values
        starting from zero, without gaps.
        """

        return self.currentIndex()

    def set_value(self, index):
        """
        Alter the current waypoint type.

        The given `index` is an `IntEnum` of the correct enum class, or
        a comparable integer. The combo box is updated to select the
        appropriate option, assuming the enum class has values starting from
        zero, without gaps.
        """

        self.setCurrentIndex(int(index))

class WaypointDirectionWidget(WaypointEnumWidget):
    """
    A table cell widget that makes it possible to select a certain line follower
    direction for the home type waypoint data associated with that row.
    """

    def __init__(self, table, item, default=0, *a, **kw):
        label = "home direction: {} ({})"
        super(WaypointDirectionWidget, self).__init__(table, item,
                                                      Line_Follower_Direction,
                                                      default, label=label,
                                                      *a, **kw)

    def sizeHint(self):
        # Disable the size hint of the widget because it is always placed in 
        # a spanned column that is large enough to hold the combo box.
        return QtCore.QSize(0, 0)

class WaypointTypeWidget(WaypointEnumWidget):
    """
    A table cell widget that makes it possible to select a certain waypoint type
    for the waypoint data associated with that row.
    """

    def __init__(self, table, item, default, *a, **kw):
        super(WaypointTypeWidget, self).__init__(table, item, Waypoint_Type,
                                                 default, label="{1}", *a, **kw)

        # Lambda functions to change a bitmask flag of the cell item to enable 
        # or disable editing and selection.
        self._enabler = lambda f: (f | QtCore.Qt.ItemIsEditable |
                                   QtCore.Qt.ItemIsSelectable |
                                   QtCore.Qt.ItemIsEnabled)
        self._disabler = lambda f: (f & ~QtCore.Qt.ItemIsEditable &
                                    ~QtCore.Qt.ItemIsSelectable &
                                    ~QtCore.Qt.ItemIsEnabled)

        # Background colors to signify the enabled or disabled state of a cell.
        self._enabled_color = QtGui.QBrush()
        self._disabled_color = QtGui.QColor("#e8e8e8")

        self._home_direction_value = 0

        self.currentIndexChanged[int].connect(self._update_row_type)

    def _update_row_type(self, index):
        """
        Update the other cells in the row of this cell widget based on the
        waypoint type.

        The `index` is the index associated with the selected combo box item,
        starting from `0`. The two cells next to this cell widget, which are
        in the "wait ID", "wait count" and "wait waypoint" columns, are enabled
        or disabled based on whether the `index` belongs to the wait type
        waypoint. For home type waypoints, another `WaypointEnumWidget` cell
        widget is added to allow inserting a home direction.
        """

        # Determine the row and column of the item (these may have changed 
        # since the cell widget was created) and deduce the range and span of 
        # the columns that are related to the wait type waypoint.
        row = self._table.row(self._item)
        col = self._table.column(self._item)
        column_count = self._table.columnCount()
        span = column_count - col - 1

        home_direction_widget = None
        old_home_widget = self._table.cellWidget(row, col + 1)
        if isinstance(old_home_widget, WaypointEnumWidget):
            self._home_direction_value = old_home_widget.get_value()

        # Determine which columns to enable/disable.
        if index + 1 == Waypoint_Type.HOME:
            disable = lambda column: False if column == col + 1 else True

            item = self._table.get_item(row, col + 1)
            home_direction_widget = WaypointDirectionWidget(self._table, item)
            home_direction_widget.set_value(self._home_direction_value)
        elif index + 1 == Waypoint_Type.WAIT:
            disable = lambda column: False
            span = 1
        else:
            disable = lambda column: True

        # Change the span of the next column. Prevent log spam by only changing 
        # it if the current or new span is more than 1.
        if span > 1 or self._table.columnSpan(row, col + 1) > 1:
            self._table.setSpan(row, col + 1, 1, span)

        self._table.setCellWidget(row, col + 1, home_direction_widget)

        # Change the state of the columns related to wait type waitpoints.
        for state_column in range(col + 1, column_count):
            item = self._table.get_item(row, state_column)
            if disable(state_column):
                item.setFlags(self._disabler(item.flags()))
                item.setBackground(self._disabled_color)
            else:
                item.setFlags(self._enabler(item.flags()))
                item.setBackground(self._enabled_color)

    def get_value(self):
        """
        Retrieve the current waypoint type value.

        The value is returned as an integer corresponding to the `Waypoint_Type`
        enumeration.
        """

        return self.currentIndex() + 1

    def set_value(self, index):
        """
        Alter the current waypoint type.

        The given `index` is a `Waypoint_Type` or comparable integer. The combo
        box is updated to select the appropriate type, and other cells in this
        row are enabled or disabled based on whether the `index` belongs to the
        wait type waypoint.
        """

        self.setCurrentIndex(index - 1)

class WaypointsTableWidget(QtGui.QTableWidget):
    """
    A table widget with specialized rows for supplying waypoint data.
    """

    menuRequested = QtCore.pyqtSignal(list, QtCore.QPoint, name='menuRequested')

    def __init__(self, columns, vehicle, *a, **kw):
        super(WaypointsTableWidget, self).__init__(*a, **kw)

        # We assume that the defaults are `None` for columns without defaults 
        # and something else for columns with defaults. The column without 
        # defaults must be the first columns in the table, otherwise the tab 
        # ordering does not match the characteristics of the columns.
        self._columns = columns

        self._vehicle = vehicle

        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([column["label"] for column in columns])
        self.insertRow(0)

        horizontalHeader = self.horizontalHeader()
        for i, column in enumerate(columns):
            if column["default"] is None:
                mode = QtGui.QHeaderView.Stretch
            else:
                mode = QtGui.QHeaderView.ResizeToContents

            horizontalHeader.setResizeMode(i, mode)

        # Create the context menu for the rows in the table.
        verticalHeader = self.verticalHeader()
        verticalHeader.setResizeMode(QtGui.QHeaderView.Fixed)
        verticalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        verticalHeader.customContextMenuRequested.connect(self._make_menu)

        self.itemChanged.connect(self._item_changed)

    def _item_changed(self, item):
        """
        Checks whether the given `item`, a `QTableWidgetItem`, is still valid.
        """

        # Only change validity when the user was editing the item.
        if self.state() != QtGui.QAbstractItemView.EditingState:
            return

        row = self.row(item)
        col = self.column(item)
        text = item.text()
        valid = True

        if text != "":
            try:
                value = self.cast_cell(row, col, text)
            except ValueError:
                valid = False

            if valid and "min" in self._columns[col]:
                valid = value >= self._columns[col]["min"]

        self._set_item_valid(item, valid)

    def _set_item_valid(self, item, valid):
        """
        Mark the cell item `item` as valid or invalid depending on `valid`.
        """

        if not valid:
            item.setBackground(QtGui.QColor("#FA6969"))
        elif item.flags() & QtCore.Qt.ItemIsEnabled:
            item.setBackground(QtGui.QBrush())

    def set_valid(self, row, column, valid):
        """
        Mark the cell in the table row `row` and column `column` as valid or
        invalid depending on `valid`.
        """

        self._set_item_valid(self.get_item(row, column), valid)

    def cast_cell(self, row, col, text):
        """
        Change the value `text` from a cell in row `row` and column `col` to
        the correct type.

        Returns the casted value. Raises a `WaypointsTableValueError` if the
        text cannot be casted to the appropriate value.
        """

        if self._columns[col]["default"] is not None:
            type_cast = type(self._columns[col]["default"])
        else:
            type_cast = float

        try:
            value = type_cast(text)
        except ValueError as e:
            raise WaypointsTableValueError(e.message, self._vehicle, row, col)

        if "offset" in self._columns[col]:
            return value - self._columns[col]["offset"]

        return value

    def get_row_data(self, row):
        """
        Retrieve the cell data from the given row number `row`.

        The cell data is returned as a list, where each value is either `None`,
        indicating that the cell was not filled, a boolean for cells with
        a check role, or the string value for other cells. The string value is
        thus not yet cast or altered for internal offsets. Cells with widgets
        in them may already have been adapted to the correct type and value.

        Additionally, a boolean is returned indicating whether the row was
        completely empty, i.e., not filled or altered.
        """

        empty = True
        data = []
        for col in range(len(self._columns)):
            widget = self.cellWidget(row, col)
            if isinstance(widget, WaypointEnumWidget):
                data.append(widget.get_value())
                continue

            item = self.item(row, col)
            # Handle unaltered column cells (no item widget), empty columns 
            # (text contents equals to empty string) and disabled cells.
            if item is None or item.text() == "":
                data.append(None)
            elif not (item.flags() & QtCore.Qt.ItemIsEnabled):
                data.append(None)
            else:
                data.append(item.text())
                empty = False

        return data, empty

    def insert_data_row(self, row, data):
        """
        Set the cell data for the given `row` from a list `data`.

        The given `row` must be a row index number where the row should be
        inserted at. If the `data` is not long enough, i.e., it does not provide
        a value for required columns, then a `ValueError` is raised.
        """

        self.insertRow(row)

        for col, column in enumerate(self._columns):
            if col >= len(data):
                if column["default"] is None:
                    # Data is required for this column, but it is not provided.
                    raise ValueError("Row #{} has missing information for column '{}'".format(row + 1, column["label"]))

                break

            widget = self.cellWidget(row, col)
            if isinstance(widget, WaypointEnumWidget):
                widget.set_value(data[col])
            elif data[col] != column["default"]:
                # Alter the data in case there is an offset for this column, 
                # but only do so when it is not the default "special" value.
                if "offset" in column:
                    item = str(data[col] + column["offset"])
                else:
                    item = str(data[col])

                self.setItem(row, col, QtGui.QTableWidgetItem(item))

    def get_item(self, row, col):
        """
        Retrieve the item for the given `row` and column `col`.

        If no item has been set for this cell yet, then it is created and the
        new `QTableWidgetItem` is returned. This is unlike `item`, which returns
        `None` if the item is not yet created due to lazy loading.
        """

        item = self.item(row, col)
        if item is None:
            item = QtGui.QTableWidgetItem()
            self.setItem(row, col, item)

        return item

    def insertRow(self, row):
        super(WaypointsTableWidget, self).insertRow(row)

        for col, column in enumerate(self._columns):
            if "widget" in column:
                item = self.get_item(row, col)
                widget = column["widget"](self, item, column["default"])
                self.setCellWidget(row, col, widget)

    def removeRows(self):
        """
        Remove all the rows in the table.
        """

        self.setRowCount(0)

    def _get_tab_index(self, next):
        """
        Determine the `QModelIndex` belonging to the next or previous item.

        The waypoints table has a special tab order that skips the columns
        with defaults that are equal to `0`, i.e., not `None` or some other
        nonzero value. It also skips cells that cannot be selected.

        If `next` is `True`, then we want to receive an index for the first
        logical item after the current item, otherwise we want the index for
        the one before it. If no such index can be found, an invalid model index
        is returned.
        """

        currentIndex = self.currentIndex()
        row = currentIndex.row()
        col = currentIndex.column()

        endRow = self.rowCount() - 1
        endCol = self.columnCount() - 1

        # Try any selectable item in the remainder of the row, or the next or 
        # previous row's start/end, or the first/last cell of the table.
        if next:
            options = [(row, j) for j in range(col+1, endCol+1)]
            options.extend([(row+1, 0), (0, 0)])
        else:
            options = [(row, j) for j in range(col-1, -1, -1)]
            options.extend([(row-1, j) for j in range(endCol, -1, -1)])
            options.append((endRow, endCol))

        for newRow, newCol in options:
            index = currentIndex.sibling(newRow, newCol)
            if index.isValid():
                # Skip cells that have a default of `0`, because those cells 
                # are more "optional" than any of the others.
                if self._columns[newCol]["default"] == 0:
                    continue

                item = self.itemFromIndex(index)
                if item is None or item.flags() & QtCore.Qt.ItemIsSelectable:
                    return index

        # Return an invalid model index if no valid next index is found.
        return QtCore.QModelIndex()

    def moveCursor(self, action, modifiers):
        if action == QtGui.QAbstractItemView.MoveNext:
            return self._get_tab_index(True)
        if action == QtGui.QAbstractItemView.MovePrevious:
            return self._get_tab_index(False)

        return super(WaypointsTableWidget, self).moveCursor(action, modifiers)

    def focusNextPrevChild(self, next):
        if self.tabKeyNavigation():
            index = self._get_tab_index(next)
            if index.isValid():
                # Focus on the item and enable the editor so that we can easily 
                # alter the waypoints using only the keyboard.
                self.setCurrentIndex(index)
                self.editItem(self.itemFromIndex(index))
                return True

            return False

        return super(WaypointsTableWidget, self).focusNextPrevChild(next)

    def _make_menu(self, position):
        """
        Create a context menu for the vertical header (row labels).
        """

        is_valid = self.indexAt(position).isValid()

        insert_row_action = QtGui.QAction("Insert row before", self)
        insert_row_action.triggered.connect(partial(self._insert_row, position))
        remove_rows_action = QtGui.QAction("Remove row(s)", self)
        remove_rows_action.setEnabled(is_valid)
        remove_rows_action.triggered.connect(partial(self._remove_rows, position))

        actions = [insert_row_action, remove_rows_action]
        self.menuRequested.emit(actions, position)

        menu = QtGui.QMenu(self)
        for action in actions:
            menu.addAction(action)

        menu.exec_(self.verticalHeader().viewport().mapToGlobal(position))

    def _insert_row(self, position):
        """
        Add one row in front of the row at the context menu position.
        """

        item = self.indexAt(position)
        row = item.row() if item.isValid() else self.rowCount()
        self.insertRow(row)
        self.selectRow(row)

    def _remove_rows(self, position):
        """
        Remove one or more selected rows from the table.

        The rows can either be selected or the row at the context menu position
        is removed.
        """

        items = self.selectionModel().selectedRows()
        if items:
            rows = [item.row() for item in items]
        else:
            rows = [self.indexAt(position).row()]

        for row in reversed(sorted(rows)):
            self.removeRow(row)
