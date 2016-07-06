from functools import partial
from PyQt4 import QtCore, QtGui

class WaypointsTableWidget(QtGui.QTableWidget):
    def __init__(self, column_labels, column_defaults, *a, **kw):
        super(WaypointsTableWidget, self).__init__(*a, **kw)

        # We assume that `len(column_labels) == len(column_defaults)`, and that 
        # the defaults are `None` for columns without defaults and something 
        # else for columns with defaults. The column without defaults must be 
        # the first columns in the table, otherwise the tab ordering does not 
        # match the characteristics of the columns.
        self._column_defaults = column_defaults

        self.setRowCount(1)
        self.setColumnCount(len(column_labels))
        self.setHorizontalHeaderLabels(column_labels)

        horizontalHeader = self.horizontalHeader()
        for i in range(len(column_labels)):
            horizontalHeader.setResizeMode(i, QtGui.QHeaderView.Stretch)

        # Create the context menu for the rows in the table.
        verticalHeader = self.verticalHeader()
        verticalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        verticalHeader.customContextMenuRequested.connect(self._make_menu)

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
        for col in range(len(self._column_defaults)):
            item = self.item(row, col)
            # Handle unaltered column cells (no item widget) and empty columns 
            # (text contents equals to empty string)
            if item is None or item.text() == "":
                data.append(None)
            else:
                data.append(item.text())
                empty = False

        return data, empty

    def removeRows(self):
        """
        Remove all the rows in the table.
        """

        for row in reversed(range(self.rowCount())):
            self.removeRow(row)

    def _get_tab_index(self, next):
        """
        Determine the `QModelIndex` belonging to the next or previous item.

        The waypoints table has a special tab order that follows the columns
        without defaults first, and only then goes to columns with defaults.

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
        if self._column_defaults[col] is not None:
            # Navigate down/up in columns with defaults, and otherwise jump to 
            # the beginning/end of the next row or the table start/end
            if next:
                options = [(row+1, col), (0, col+1), (0, 0)]
            else:
                options = [(row-1, col), (endRow, col-1), (endRow, endCol)]
        else:
            # Navigate right/left in columns without defaults, but skip columns 
            # with defaults, by going to the first/last column without defaults 
            # of the next/previous row if one would go to such column with 
            # defaults. If no such row exists anymore, go to the first/last 
            # column with defaults on the first/last row.
            lastCol = max(enumerate(self._column_defaults), key=lambda x: x[0] if x[1] is None else 0)[0]
            if next:
                options = [(row+1, 0), (0, col+1), (0, 0)]
                if col != lastCol:
                    options[0:0] = [(row, col+1)]
            else:
                options = [(row, col-1), (row-1, lastCol), (endRow, endCol)]

        for newRow, newCol in options:
            index = currentIndex.sibling(newRow, newCol)
            if index.isValid():
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
