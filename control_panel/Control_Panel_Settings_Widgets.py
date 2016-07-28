import re
from PyQt4 import QtCore, QtGui
from Control_Panel_Settings_Form_Widgets import *

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

        self._horizontal_mode = self.isHorizontal()
        self._create_layout()

        self._first = True
        self._add_settings(self._settings)

    def _add_settings(self, settings):
        for key, info in sorted(settings.get_info(), key=lambda x: x[0]):
            valueWidget = self.make_value_widget(settings, key, info)

            self._widgets[key] = self._add_group_box(key, info, valueWidget)
            self._value_widgets[key] = valueWidget
            self.resize_widget(key)
            self._first = False

    def isHorizontal(self):
        """
        Check whether the widget's form items should be laid out in a most
        horizontal way possible.
        """

        return False

    def _get_box_layout(self):
        """
        Create a `QLayout` object that is appropriate to the current layout
        mode (horizontal or vertical).
        """

        if self._horizontal_mode:
            return QtGui.QHBoxLayout()

        return QtGui.QVBoxLayout()

    def _create_layout(self):
        """
        Set up the main layout that is appropriate to the current layout mode
        (horizontal or vertical).
        """

        self._layout = self._get_box_layout()
        if not self._horizontal_mode:
            self._add_title_label()
            self._add_parent_button()

        self.setLayout(self._layout)

    def get_title(self):
        """
        Get a titular name of the settings widget.
        """

        return "{} ({})".format(self._settings.name, self._component)

    def _add_title_label(self):
        titleLabel = QtGui.QLabel(self.get_title())
        titleLabel.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        titleLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        titleLabel.setStyleSheet("QLabel { font-size: 24px; background: white }")
        titleLabel.setWordWrap(True)

        self._layout.addWidget(titleLabel)

    def _add_parent_button(self):
        if self._settings.parent is not None:
            parentButton = QtGui.QCommandLinkButton(self._settings.parent.name,
                                                    "Go to parent ({})".format(self._settings.parent.component_name))
            policy = parentButton.sizePolicy()
            policy.setVerticalPolicy(QtGui.QSizePolicy.Fixed)
            parentButton.setSizePolicy(policy)
            parentButton.clicked.connect(self._trigger_parent_clicked)

            self._layout.addWidget(parentButton)

    def _add_group_box(self, key, info, valueWidget):
        if not self._first:
            # Add a line separator between the group box widgets.
            line = QtGui.QFrame()
            line.setFrameShape(QtGui.QFrame.HLine)
            line.setFrameShadow(QtGui.QFrame.Sunken)
            self._layout.addWidget(line)

        # Create the form and its rows.
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

        valueLabel = QtGui.QLabel("Value:")
        formLayout.addRow(valueLabel, valueWidget)

        # Create the group box.
        groupBox = QtGui.QGroupBox(key)

        groupBox.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        for action in valueWidget.get_actions():
            groupBox.addAction(action)

        groupBox.setLayout(formLayout)
        self._layout.addWidget(groupBox)

        return groupBox

    def get_settings(self):
        """
        Retrieve the `Settings` object for this settings widget.
        """

        return self._settings

    def get_setting_widget(self, key):
        """
        Retrieve a specific `QtGui.QWidget` that wraps the input of a value for
        the given settings key `key`.

        If the settings widget does not have a widget for that key, then this
        method raises a `KeyError`.
        """

        if key not in self._widgets:
            raise KeyError("Setting '{}' in component '{}' does not have a widget.".format(key, self._component))

        return self._widgets[key]

    def get_value_widget(self, key):
        """
        Retrieve a specific `FormWidget` for the input of a value for the given
        settings key `key`.

        If the settings widget does not have a widget for that key, then this
        method raises a `KeyError`.
        """

        if key not in self._value_widgets:
            raise KeyError("Setting '{}' in component '{}' does not have a widget.".format(key, self._component))

        return self._value_widgets[key]

    def format_type(self, info):
        """
        Retrieve a human-readable version for the settings type in the settings
        information dictionary `info`.
        """

        return self._type_names[info["type"]]

    def make_value_widget(self, settings, key, info, horizontal=None):
        """
        Create a `FormWidget` for inputting the value for a specific settings
        key `key` with information dictionary `info`.

        This widget can be used inside other widgets in the settings widget,
        or for subwidgets in an existing `FormWidget`. This method picks the
        best type of `FormWidget` for the given settings type.

        If `horizontal` is provided, the `FormWidget` will be laid out as much
        as possible in the given direction. Otherwise, this defaults to the
        settings widget's `isHorizontal` mode.
        """

        if horizontal is None:
            horizontal = self._horizontal_mode

        choices = self._arguments.get_choices(info)
        if choices is not None:
            widget = ChoicesFormWidget(self, key, info, settings, horizontal)
            widget.add_choices(choices)
        else:
            widget_type = self._type_widgets[info["type"]]
            widget = widget_type(self, key, info, settings, horizontal)

        return widget

    def get_values(self):
        """
        Retrieve the current values from the input widgets that have changed
        from the default.

        The returned values are two dictionaries. The first dictionary contains
        the settings keys and the changed values, while the second dictionary
        contains the allowed state of each value widget by their settings key.
        """

        values = {}
        allowed = {}
        for key, widget in self._value_widgets.iteritems():
            allowed[key] = widget.is_value_allowed()
            if not widget.is_value_default():
                values[key] = widget.get_value()

        return values, allowed

    def get_all_values(self):
        """
        Retrieve the current values from the input widgets, even when they are
        the same as the default.

        The returned values are a dictionary and a list. The dictionary contains
        the settings keys and the current values, while the second list contains
        the settings keys that have disallowed values.
        """

        values = {}
        disallowed = []
        for key, widget in self._value_widgets.iteritems():
            if not widget.is_value_allowed():
                disallowed.append(key)

            values[key] = widget.get_value()

        return values, disallowed

    def check_disallowed(self, disallowed):
        """
        Check whether all values from `get_all_values` are allowed.

        Raises a `ValueError` with a corresponding message if any disallowed
        values are found.
        """

        if disallowed:
            keys = ", ".join("'{}'".format(key) for key in disallowed)
            raise ValueError("The following settings from component '{}' have incorrect values: {}".format(self.get_title(), keys))

    def _trigger_parent_clicked(self):
        self.parentClicked.emit(self._settings.parent.component_name)

    def resize_widget(self, key):
        """
        Handle resizing the value widget contents for setting key `key`.
        """

        pass

    def _get_short_label(self, key, info):
        return "{}:".format(info["short"] if "short" in info else key)

class SettingsTableWidget(QtGui.QTableWidget, SettingsWidget):
    def __init__(self, arguments, component, include_parent=True, *a, **kw):
        self._rows = {}
        QtGui.QTableWidget.__init__(self, *a, **kw)
        SettingsWidget.__init__(self, arguments, component, *a, **kw)

        if self._settings.parent is not None and include_parent:
            self._add_settings(self._settings.parent)

    def _create_layout(self):
        # Create the key and value columns.
        self.setColumnCount(2)

        # Let the columns take up the entire width of the table.
        for index in range(2):
            self.horizontalHeader().setResizeMode(index, QtGui.QHeaderView.Stretch)

        self.verticalHeader().setResizeMode(QtGui.QHeaderView.Fixed)

        # Hide the horizontal and vertical headers.
        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        # Disable tab key navigation of the table so the tab key navigation of 
        # form input still works.
        self.setTabKeyNavigation(False)

    def resize_widget(self, key):
        if key not in self._rows:
            return

        widget = self._widgets[key]
        size = max(widget.height(), widget.sizeHint().height())
        self.verticalHeader().resizeSection(self._rows[key], size)

    def _add_group_box(self, key, info, valueWidget):
        # Format the help message as a tooltip. If it contains multiple 
        # sentences, then each sentence spans one line.
        tooltip = self._arguments.get_help(key, info)
        tooltip = re.sub(r'([^.]+\.)( |$)',
                         lambda m: "<nobr>{}</nobr>{}".format(m.group(1), "<br>" if m.group(2) else ""),
                         tooltip)

        # Create the label cell item.
        label = QtGui.QTableWidgetItem(self._get_short_label(key, info))
        label.setToolTip(tooltip)
        label.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        label.setFlags(label.flags() & ~QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsSelectable)

        # Create the table row and insert the label and value cells.
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, label)
        self.setCellWidget(row, 1, valueWidget)

        self._rows[key] = row

        return valueWidget
