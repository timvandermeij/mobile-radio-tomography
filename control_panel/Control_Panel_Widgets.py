import os
import re
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
        verticalHeader.customContextMenuRequested.connect(partial(self._make_menu))

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

# Ported from https://github.com/Frodox/qt-line-edit-with-clear-button
# Qt5's QLineEdit has this built in via the clearButtonEnabled.
# We emulate its behavior here.
class QLineEditClear(QtGui.QLineEdit):
    def __init__(self, *a, **kw):
        super(QLineEditClear, self).__init__(*a, **kw)

        self.clearButton = QLineEditToolButton(self)
        self.clearButton.setIcon(QtGui.QIcon("assets/edit-clear.png"))
        self.clearButton.hide()

        self.clearButton.clicked.connect(self.clear)
        self.textChanged.connect(self.updateCloseButton)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.clear()
            self.clearFocus()

        super(QLineEditClear, self).keyPressEvent(event)

    def resizeEvent(self, event):
        self.clearButton.resizeEvent(event)

    def updateCloseButton(self, text):
        self.clearButton.setVisible(not text.isEmpty())

class QLineEditToolButton(QtGui.QToolButton):
    def __init__(self, parent, *a, **kw):
        super(QLineEditToolButton, self).__init__(parent, *a, **kw)

        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setStyleSheet("QToolButton { border: none; padding: 0px; }")

        frameWidth = self._getParentFrameWidth()
        width = self.sizeHint().width() + frameWidth + 1
        parent.setStyleSheet("padding-right: {}px;".format(width))

        msz = parent.minimumSizeHint()
        # Source assumed square icon here, but we do not.
        fill = frameWidth * 2 + 2
        parent.setMinimumSize(max(msz.width(), self.width() + fill),
                              max(msz.height(), self.height() + fill))

    def _getParentFrameWidth(self):
        return self.parent().style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)

    def resizeEvent(self, event):
        size = self.sizeHint()
        frameWidth = self._getParentFrameWidth()
        rect = self.parent().rect()
        self.move(rect.right() - frameWidth - size.width(),
                  (rect.bottom() + 1 - size.height())/2)


class SettingsWidget(QtGui.QWidget):
    parentClicked = QtCore.pyqtSignal(str, name='parentClicked')

    def __init__(self, arguments, component, *a, **kw):
        super(SettingsWidget, self).__init__(*a, **kw)
        self._type_names = {
            "int": "Integer",
            "float": "Floating point",
            "bool": "Boolean",
            "string": "String",
            "file": "File name",
            "class": "Class name",
            "list": "List",
            "tuple": "Tuple"
        }
        self._type_widgets = {
            "int": IntegerFormWidget,
            "float": FloatFormWidget,
            "bool": BooleanFormWidget,
            "string": TextFormWidget, # Unless "choices" is supplied
            "file": FileFormWidget,
            "class": TextFormWidget, # Unless "choices" is supplied
            "list": ListFormWidget,
            "tuple": ListFormWidget,
            "dict": DictFormWidget
        }

        self._component = component
        self._arguments = arguments
        self._settings = self._arguments.get_settings(self._component)

        self._widgets = {}
        self._value_widgets = {}

        layout = QtGui.QVBoxLayout()

        titleLabel = QtGui.QLabel("{} ({})".format(self._settings.name, self._component))
        titleLabel.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        titleLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        titleLabel.setStyleSheet("QLabel { font-size: 24px; background: white }")
        titleLabel.setWordWrap(True)

        layout.addWidget(titleLabel)

        if self._settings.parent is not None:
            parentButton = QtGui.QCommandLinkButton(self._settings.parent.name, "Go to parent ({})".format(self._settings.parent.component_name))
            policy = parentButton.sizePolicy()
            policy.setVerticalPolicy(QtGui.QSizePolicy.Fixed)
            parentButton.setSizePolicy(policy)
            parentButton.clicked.connect(self._trigger_parent_clicked)

            layout.addWidget(parentButton)

        first = True
        for key, info in self._settings.get_info():
            if first:
                first = False
            else:
                line = QtGui.QFrame()
                line.setFrameShape(QtGui.QFrame.HLine)
                line.setFrameShadow(QtGui.QFrame.Sunken)
                layout.addWidget(line)

            formLayout = QtGui.QFormLayout()
            formLayout.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)

            typeLabel = QtGui.QLabel(self.format_type(info))
            formLayout.addRow("Type:", typeLabel)

            descriptionLabel = QtGui.QLabel("Description:")
            descriptionLabel.setAlignment(QtCore.Qt.AlignTop)
            description = QtGui.QLabel(self._arguments.get_help(key, info))
            description.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
            description.setWordWrap(True)
            formLayout.addRow(descriptionLabel, description)

            valueWidget = self.make_value_widget(key, info)

            valueLabel = QtGui.QLabel("Value:")
            formLayout.addRow(valueLabel, valueWidget)

            groupBox = QtGui.QGroupBox(key)

            groupBox.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            for action in valueWidget.get_actions():
                groupBox.addAction(action)

            groupBox.setLayout(formLayout)
            layout.addWidget(groupBox)

            self._value_widgets[key] = valueWidget
            self._widgets[key] = groupBox

        self.setLayout(layout)

    def get_settings(self):
        return self._settings

    def get_setting_widget(self, key):
        if key not in self._widgets:
            raise KeyError("Setting '{}' in component '{}' does not have a widget.".format(key, self._component))

        return self._widgets[key]

    def format_type(self, info):
        return self._type_names[info["type"]]

    def make_value_widget(self, key, info):
        choices = self._arguments.get_choices(info)
        if choices is not None:
            widget = ChoicesFormWidget(self, key, info)
            widget.add_choices(choices)
        else:
            widget_type = self._type_widgets[info["type"]]
            widget = widget_type(self, key, info)

        return widget

    def get_values(self):
        values = {}
        for key, widget in self._value_widgets.iteritems():
            if not widget.is_value_default():
                values[key] = widget.get_value()

        return values

    def _trigger_parent_clicked(self):
        self.parentClicked.emit(self._settings.parent.component_name)

class FormWidget(QtGui.QWidget):
    def __init__(self, form, key, info, *a, **kw):
        super(FormWidget, self).__init__(*a, **kw)
        self.form = form
        self.key = key
        self.info = info

        reset_action = QtGui.QAction("Reset to current value", self)
        reset_action.triggered.connect(self.reset_value)
        default_action = QtGui.QAction("Reset to default value", self)
        default_action.triggered.connect(self.set_default_value)
        self._actions = [reset_action, default_action]

        self.setup_form()

    def setup_form(self):
        pass

    def get_actions(self):
        return self._actions

    def get_value(self):
        raise NotImplementedError("Subclasses must implement `get_value`")

    def set_value(self, value):
        raise NotImplementedError("Subclasses must implement `set_value(value)`")

    def reset_value(self):
        self.set_value(self.info["value"])

    def set_default_value(self):
        self.set_value(self.info["default"])

    def is_value_changed(self):
        return self.get_value() != self.info["value"]

    def is_value_default(self):
        return self.get_value() == self.info["default"]

class BooleanFormWidget(FormWidget):
    def setup_form(self):
        self._enabledButton = QtGui.QRadioButton("Enabled")
        self._disabledButton = QtGui.QRadioButton("Disabled")

        self.reset_value()

        buttonGroup = QtGui.QButtonGroup()
        buttonGroup.addButton(self._enabledButton)
        buttonGroup.addButton(self._disabledButton)

        buttonLayout = QtGui.QVBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._enabledButton)
        buttonLayout.addWidget(self._disabledButton)

        self.setLayout(buttonLayout)

    def get_value(self):
        return self._enabledButton.isChecked()

    def set_value(self, value):
        self._enabledButton.setChecked(value)
        self._disabledButton.setChecked(not value)

class QLineEditValidated(QtGui.QLineEdit):
    def __init__(self, *a, **kw):
        QtGui.QLineEdit.__init__(self, *a, **kw)
        self._background_color = ""

    def setValidator(self, v):
        super(QLineEditValidated, self).setValidator(v)
        validator = self.validator()
        if validator is not None:
            self.textChanged.connect(self._validate)
        else:
            self.textChanged.disconnect(self._validate)

    def set_background_color(self, color):
        self._background_color = color

        decl = "background-color: "
        styleSheet = str(self.styleSheet())
        if color == "":
            replace = ""
        else:
            replace = r"\1{}\3".format(color)

        newSheet, count = re.subn("({})(.*)(;)".format(decl), replace, styleSheet)
        if count == 0 and color != "":
            newSheet = styleSheet + decl + color + ";"

        self.setStyleSheet(newSheet)

    def get_background_color(self):
        return self._background_color

    def _validate(self, text):
        pos = self.cursorPosition()
        state, newpos = self.validator().validate(text, pos)
        if state != QtGui.QValidator.Acceptable:
            color = "#FA6969"
        else:
            color = "#8BD672"

        self.set_background_color(color)

        if newpos != pos:
            self.setCursorPosition(pos)

class TextFormWidget(QLineEditValidated, FormWidget):
    def __init__(self, form, key, info, *a, **kw):
        # Qt does not understand the concept of multiple inheritance, since it 
        # is written in C++. Therefore, the QLineEdit must be the first class 
        # we inherit from, otherwise setText (a slot method) does not function.
        # However, we now need to call the FormWidget initializer explicitly, 
        # since it sets up member variables and is not called by QLineEdit.
        # See http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/ 
        # for more details.
        QLineEditValidated.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, *a, **kw)
        self._background_color = ""

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        for action in self._actions:
            menu.addAction(action)

        menu.setStyleSheet("background-color: base")
        menu.exec_(event.globalPos())
        menu.clear()

    def setup_form(self):
        self.reset_value()
        self.editingFinished.connect(self._format)

    def get_value(self):
        text = self.text()
        validator = self.validator()
        if validator is not None:
            state, pos = validator.validate(text, 0)
            if state != QtGui.QValidator.Acceptable:
                return self.info["value"]

        return str(text)

    def set_value(self, value):
        self.setText(self.format_value(value))

    def _format(self):
        self.setText(self.format_value(self.text()))

    def format_value(self, value):
        return str(value) if value is not None else ""

class FileFormatValidator(QtGui.QRegExpValidator):
    def __init__(self, form_widget, *a, **kw):
        super(FileFormatValidator, self).__init__(*a, **kw)
        self.form_widget = form_widget
        self.key = self.form_widget.key
        self.info = self.form_widget.info
        self.required = "required" in self.info and self.info["required"]
        self.settings = self.form_widget.form.get_settings()

        regexp = self.settings.make_format_regex(self.info["format"])
        self.setRegExp(QtCore.QRegExp(regexp))

    def validate(self, input, pos):
        if input == "":
            input = None

        try:
            self.settings.check_format(self.key, self.info, input)
            return QtGui.QValidator.Acceptable, pos
        except ValueError as e:
            return QtGui.QValidator.Intermediate, pos

class FileFormWidget(TextFormWidget):
    def setup_form(self):
        super(FileFormWidget, self).setup_form()

        self.openButton = QLineEditToolButton(self)
        self.openButton.setIcon(QtGui.QIcon("assets/file-open.png"))

        self.openButton.clicked.connect(self._open_file)

        if "format" in self.info:
            self.setValidator(FileFormatValidator(self))

    def format_value(self, value):
        if value is None or value == "":
            return ""

        if "format" in self.info:
            try:
                return self.form.get_settings().check_format(self.key, self.info, value)
            except ValueError:
                pass

        return value

    def get_value(self):
        text = super(FileFormWidget, self).get_value()
        if text == "":
            return None

        return text

    def _open_file(self):
        if "format" in self.info:
            directory, file_format = os.path.split(self.info["format"])
            file_type = os.path.splitext(file_format)[1]
            file_filter = "{} files (*{})".format(file_type[1:].upper(), file_type)
        else:
            directory = ""
            file_filter = ""

        work_dir = os.getcwd() + "/"

        color = self.get_background_color()
        self.set_background_color("")
        file_name = QtGui.QFileDialog.getOpenFileName(self, "Select file",
                                                      work_dir + directory,
                                                      file_filter)

        if file_name == "":
            self.set_background_color(color)
            return

        file_name = os.path.relpath(str(file_name), work_dir)

        self.setText(self.format_value(file_name))

    def resizeEvent(self, event):
        self.openButton.resizeEvent(event)

class NumericFormWidget(TextFormWidget):
    def setup_form(self):
        self._formatter = None
        self._caster = None
        super(NumericFormWidget, self).setup_form()

    def setValidator(self, v):
        super(NumericFormWidget, self).setValidator(v)

        validator = self.validator()
        if validator is not None:
            if "min" in self.info:
                validator.setBottom(self.info["min"])
            if "max" in self.info:
                validator.setTop(self.info["max"])

    def set_formatter(self, formatter):
        self._formatter = formatter
        self.reset_value()

    def format_value(self, value):
        if self._formatter is not None:
            return self._formatter(value)

        return super(NumericFormWidget, self).format_value(value)

    def set_caster(self, caster):
        self._caster = caster

    def get_value(self):
        text = super(NumericFormWidget, self).get_value()
        if self._caster is not None:
            try:
                return self._caster(text)
            except (TypeError, ValueError):
                pass

        return text

class NumericSliderFormWidget(FormWidget):
    def setup_form(self):
        self._valueWidget = NumericFormWidget(self.form, "{}-num".format(self.key), self.info)
        self._slider = None

        self._layout = QtGui.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._valueWidget)

        self.setLayout(self._layout)

    def has_slider(self):
        return "min" in self.info and "max" in self.info

    def set_slider(self, slider):
        self._slider = slider
        self._slider.setValue(self._value_to_slider(self.info["value"]))

        self._slider.valueChanged.connect(self._handle_slider)
        self._valueWidget.textEdited.connect(self._update_slider)

        self._layout.addWidget(self._slider)

    def setValidator(self, v):
        self._valueWidget.setValidator(v)

    def set_formatter(self, formatter):
        self._valueWidget.set_formatter(formatter)

    def set_caster(self, caster):
        self._valueWidget.set_caster(caster)

    def get_value(self):
        return self._valueWidget.get_value()

    def set_value(self, value):
        self._valueWidget.set_value(value)
        if self._slider is not None:
            self._update_slider(self._valueWidget.text())

    def _slider_to_value(self, value):
        minimum = self._slider.minimum()
        maximum = self._slider.maximum()
        scale = (float(value) - minimum) / (maximum - minimum)
        return self.info["min"] + scale * (self.info["max"] - self.info["min"])

    def _value_to_slider(self, value):
        if value is None:
            value = 0.0

        minimum = self._slider.minimum()
        maximum = self._slider.maximum()
        scale = (float(value) - self.info["min"]) / (self.info["max"] - self.info["min"])
        return int(minimum + scale * (maximum - minimum))

    def _handle_slider(self, value):
        value = self._slider_to_value(value)
        self._valueWidget.setText(self._valueWidget.format_value(value))

    def _update_slider(self, text):
        try:
            value = self._value_to_slider(text)
        except ValueError:
            return

        self._slider.setValue(value)

class IntegerFormWidget(NumericSliderFormWidget):
    def setup_form(self):
        super(IntegerFormWidget, self).setup_form()
        self.set_formatter(self.format_value)
        self.set_caster(int)
        self.setValidator(QtGui.QIntValidator())

        if self.has_slider():
            slider = QtGui.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(self.info["min"], self.info["max"])
            self.set_slider(slider)

    def format_value(self, value):
        return "{:d}".format(int(value) if value is not None else 0)

class FloatFormWidget(NumericSliderFormWidget):
    def setup_form(self):
        super(FloatFormWidget, self).setup_form()
        self.set_formatter(self.format_value)
        self.set_caster(float)
        self.setValidator(QtGui.QDoubleValidator())
        if self.has_slider():
            slider = QtGui.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, 100)
            self.set_slider(slider)

    def format_value(self, value):
        value = "{:f}".format(float(value) if value is not None else 0.0)
        value = value.rstrip('0')
        if len(value) == 0 or value[-1] == '.':
            value += '0'

        return value

class ListFormWidget(FormWidget):
    def setup_form(self):
        if "length" in self.info:
            self._layout = QtGui.QHBoxLayout()
        else:
            self._layout = QtGui.QVBoxLayout()

        self._layout.setContentsMargins(0, 0, 0, 0)

        self._sub_widgets = []

        self._values = self._format_list(self.info["value"])
        self._defaults = self._format_list(self.info["default"])
        for i in range(len(self._values)):
            self._add_to_list()

        if "length" not in self.info:
            addButton = QtGui.QToolButton()
            addButton.setIcon(QtGui.QIcon("assets/list-add.png"))
            addButton.setText("Add item")
            addButton.setToolTip("Add another item element to the list")
            addButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
            addButton.clicked.connect(self._add_to_list)
            self._layout.addWidget(addButton)

        self.setLayout(self._layout)

    def _format_list(self, value):
        if value is None:
            if "length" in self.info:
                return [None]*self.info["length"]

            return []

        return value

    def _add_to_list(self, checked=False):
        position = len(self._sub_widgets)

        if len(self._values) > position:
            sub_value = self._values[position]
        else:
            sub_value = None

        if len(self._defaults) > position:
            sub_default = self._defaults[position]
        else:
            sub_default = None

        sub_info = self.info.copy()
        sub_info["type"] = sub_info.pop("subtype")
        if "length" in sub_info:
            del sub_info["length"]

        sub_info["value"] = sub_value
        sub_info["default"] = sub_default
        sub_widget = self.form.make_value_widget("{}-{}".format(self.key, position), sub_info)

        self._sub_widgets.append(sub_widget)

        if "length" in self.info:
            self._layout.insertWidget(position, sub_widget)
        else:
            itemLayout = QtGui.QHBoxLayout()
            itemLayout.setContentsMargins(0, 0, 0, 0)

            removeButton = QtGui.QToolButton()
            removeButton.setIcon(QtGui.QIcon("assets/list-remove.png"))
            removeButton.setText("Remove")
            removeButton.setToolTip("Remove this list item element")
            removeButton.setToolButtonStyle(QtCore.Qt.ToolButtonFollowStyle)
            removeButton.clicked.connect(lambda: self._remove_item(itemLayout, sub_widget, removeButton))

            itemLayout.addWidget(sub_widget)
            itemLayout.addWidget(removeButton)
            self._layout.insertLayout(position, itemLayout)

    def _remove_item(self, itemLayout, sub_widget, removeButton):
        self._layout.removeItem(itemLayout)
        sub_widget.setParent(None)
        removeButton.setParent(None)
        removeButton.close()
        itemLayout.deleteLater()
        self._layout.invalidate()
        self._sub_widgets.remove(sub_widget)

    def get_value(self):
        return [sub_widget.get_value() for sub_widget in self._sub_widgets]

    def set_value(self, value):
        # Replace values in item widgets, add widgets to the list if necessary.
        for position, sub_value in enumerate(value):
            if position >= len(self._sub_widgets):
                self._add_to_list()

            self._sub_widgets[position].set_value(sub_value)

        # Remove item widgets not having a value anymore.
        for index in xrange(len(value), len(self._sub_widgets)):
            item = self._layout.itemAt(len(value))
            if item.layout():
                self._remove_item(item, item.itemAt(0).widget(), item.itemAt(1).widget())
            else:
                self._layout.removeItem(item)

class DictFormWidget(FormWidget):
    def setup_form(self):
        self._sub_widgets = {}

        formLayout = QtGui.QFormLayout()
        for key, value_info in self.info["dictinfo"].iteritems():
            sub_info = value_info.copy()
            if self.info["default"] is not None:
                sub_info["value"] = self.info["value"][key]
                sub_info["default"] = self.info["default"][key]
            else:
                sub_info.update({"value": None, "default": None})

            key_text = "{} ({}):".format(key, self.form.format_type(sub_info))
            keyLabel = QtGui.QLabel(key_text)

            subWidget = self.form.make_value_widget("{}-{}".format(self.key, key), sub_info)
            formLayout.addRow(keyLabel, subWidget)

            self._sub_widgets[key] = subWidget

        self.setLayout(formLayout)

    def get_value(self):
        return dict((key, subWidget.get_value()) for key, subWidget in self._sub_widgets.iteritems())

    def set_value(self, value):
        for key, subWidget in self._sub_widgets.iteritems():
            subWidget.set_value(value[key])

class ChoicesFormWidget(QtGui.QComboBox, FormWidget):
    def __init__(self, form, key, info, *a, **kw):
        QtGui.QLineEdit.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, *a, **kw)
        self._types = {
            "int": int,
            "string": str,
            "float": float
        }

    def add_choices(self, choices):
        if self.count() == 0:
            if "required" in self.info and not self.info["required"]:
                choices[0:0] = [""]

        for i, choice in enumerate(choices):
            self.addItem(str(choice))
            if choice == self.info["value"]:
                self.setCurrentIndex(i)

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        for action in self._actions:
            menu.addAction(action)

        menu.exec_(event.globalPos())
        menu.clear()

    def get_value(self):
        if self.info["type"] in self._types:
            type_cast = self._types[self.info["type"]]
        else:
            type_cast = str

        return type_cast(self.currentText())

    def set_value(self, value):
        index = self.findText(str(value))
        self.setCurrentIndex(index)
