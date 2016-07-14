from functools import partial
from PyQt4 import QtCore, QtGui
from ..waypoint.Waypoint import Waypoint_Type

class WaypointTypeWidget(QtGui.QComboBox):
    """
    A table cell widget that makes it possible to select a certain waypoint type
    for the waypoint data associated with that row.
    """

    def __init__(self, table, row, col, default, *a, **kw):
        super(WaypointTypeWidget, self).__init__(*a, **kw)

        self._table = table
        self._row = row
        self._col = col

        self.addItems([item.name.lower() for item in iter(Waypoint_Type)])

        self.currentIndexChanged[int].connect(self._update_row_type)
        self.setCurrentIndex(default - 1)

    def _update_row_type(self, index):
        if index + 1 != Waypoint_Type.WAIT:
            flagger = lambda f: f & ~QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEnabled
            color = QtGui.QColor("#e8e8e8")
        else:
            flagger = lambda f: f | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            color = QtGui.QBrush()

        for i in range(1, 3):
            item = self._table.item(self._row, self._col + i)
            if item is None:
                item = QtGui.QTableWidgetItem()
                self._table.setItem(self._row, self._col + i, item)

            item.setFlags(flagger(item.flags()))
            item.setBackground(color)

    def get_value(self):
        return self.currentIndex() + 1

    def set_value(self, index):
        self.setCurrentIndex(index - 1)

class WaypointsTableWidget(QtGui.QTableWidget):
    """
    A table widget with specialized rows for supplying waypoint data.
    """

    def __init__(self, columns, *a, **kw):
        super(WaypointsTableWidget, self).__init__(*a, **kw)

        # We assume that the defaults are `None` for columns without defaults 
        # and something else for columns with defaults. The column without 
        # defaults must be the first columns in the table, otherwise the tab 
        # ordering does not match the characteristics of the columns.
        self._columns = columns

        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([column["label"] for column in columns])
        self.insertRow(0)

        horizontalHeader = self.horizontalHeader()
        for i in range(len(columns)):
            horizontalHeader.setResizeMode(i, QtGui.QHeaderView.Stretch)

        # Create the context menu for the rows in the table.
        verticalHeader = self.verticalHeader()
        verticalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        verticalHeader.customContextMenuRequested.connect(self._make_menu)

        self.itemChanged.connect(self._item_changed)

    def _item_changed(self, item):
        """
        Checks whether the given `item`, a `QTableWidgetItem`, is still valid.
        """

        col = self.column(item)
        text = item.text()
        valid = True

        if text != "":
            try:
                value = self.cast_cell(col, item.text())
            except ValueError:
                valid = False

            if valid and "min" in self._columns[col]:
                valid = value >= self._columns[col]["min"]

        if not valid:
            item.setBackground(QtGui.QColor("#FA6969"))
        elif item.flags() & QtCore.Qt.ItemIsEnabled:
            item.setBackground(QtGui.QBrush())

    def cast_cell(self, col, text):
        """
        Change the value `text` from a cell in column `col` to correct type.

        Returns the casted value. Raises a `ValueError` if the text cannot be
        casted to the appropriate value.
        """

        if self._columns[col]["default"] is not None:
            type_cast = type(self._columns[col]["default"])
        else:
            type_cast = float

        return type_cast(text)

    def get_row_data(self, row):
        """
        Retrieve the cell data from the given row number `row`.

        The cell data is returned as a list, where each value is either `None`,
        indicating that the cell was not filled, a boolean for cells with
        a check role, or the string value for other cells.

        Additionally, a boolean is returned indicating whether the row was
        completely empty, i.e., not filled or altered.
        """

        empty = True
        data = []
        for col, column in enumerate(self._columns):
            if "widget" in column:
                widget = self.cellWidget(row, col)
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

            if "widget" in column:
                widget = self.cellWidget(row, col)
                widget.set_value(data[col])
            elif data[col] != column["default"]:
                item = str(data[col])
                self.setItem(row, col, QtGui.QTableWidgetItem(item))

    def insertRow(self, row):
        super(WaypointsTableWidget, self).insertRow(row)

        for col, column in enumerate(self._columns):
            if "widget" in column:
                widget = column["widget"](self, row, col, column["default"])
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
                self.setCurrentIndex(index)
                self.editItem(self.itemFromIndex(index))
                return True

            return False

        return super(WaypointsTableWidget, self).focusNextPrevChild(next)

    def _make_menu(self, position):
        """
        Create a context menu for the vertical header (row labels).
        """

        menu = QtGui.QMenu(self)

        insert_row_action = QtGui.QAction("Insert row before", self)
        insert_row_action.triggered.connect(partial(self._insert_row, position))
        remove_rows_action = QtGui.QAction("Remove row(s)", self)
        remove_rows_action.triggered.connect(partial(self._remove_rows, position))

        menu.addAction(insert_row_action)
        menu.addAction(remove_rows_action)

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
