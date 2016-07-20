import os
import string
from PyQt4 import QtCore, QtGui
from Control_Panel_Widgets import QLineEditValidated, QLineEditToolButton

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

class SettingsToolbarWidget(SettingsWidget):
    def isHorizontal(self):
        return True

    def _add_group_box(self, key, info, valueWidget):
        labelWidget = QtGui.QLabel(self._get_short_label(key, info))
        labelWidget.setToolTip(self._arguments.get_help(key, info))
        self._layout.addWidget(labelWidget)
        self._layout.addWidget(valueWidget)

        return valueWidget

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
        label = QtGui.QTableWidgetItem(self._get_short_label(key, info))
        label.setToolTip(self._arguments.get_help(key, info))
        label.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        label.setFlags(label.flags() & ~QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsSelectable)

        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, label)
        self.setCellWidget(row, 1, valueWidget)

        self._rows[key] = row

        return valueWidget

class FormWidget(QtGui.QWidget):
    def __init__(self, form, key, info, settings, horizontal=False, *a, **kw):
        super(FormWidget, self).__init__(*a, **kw)
        self.form = form
        self.key = key
        self.info = info
        self.settings = settings
        self.horizontal = horizontal

        reset_action = QtGui.QAction("Reset to current value", self)
        reset_action.triggered.connect(self.reset_value)
        default_action = QtGui.QAction("Reset to default value", self)
        default_action.triggered.connect(self.set_default_value)
        self._actions = [reset_action, default_action]

        self.setup_form()

    def setup_form(self):
        """
        Setup the form widget's layout and other properties.
        """

        pass

    def get_actions(self):
        """
        Get a list of context menu actions for the form widget.
        """

        return self._actions

    def get_value(self):
        """
        Retrieve the current value of the form widget input.
        """

        raise NotImplementedError("Subclasses must implement `get_value`")

    def set_value(self, value):
        """
        Change the current value of the form widget input.

        This might only change the displayed state or even be ignored, and may
        not be reflected in `get_value`. For default (or overridden default)
        values, this is however desirable.
        """

        raise NotImplementedError("Subclasses must implement `set_value(value)`")

    def reset_value(self):
        """
        Reset the value to the value it was at the start.

        This is the overridden value from the current settings or the command
        line arguments.
        """

        self.set_value(self.info["value"])

    def set_default_value(self):
        """
        Reset the value to the factory defaults.

        This is the value in the settings defaults specification.
        """

        self.set_value(self.info["default"])

    def is_value_changed(self):
        """
        Check whether the current value is different from the overridden
        default.
        """

        return self.get_value() != self.info["value"]

    def is_value_default(self):
        """
        Check whether the current value is the same as the factory default.
        """
        return self.get_value() == self.info["default"]

    def is_value_allowed(self):
        """
        Check whether the current value is acceptable for this setting, as far
        as the form widget is able to know.
        """

        return True

class BooleanFormWidget(FormWidget):
    def setup_form(self):
        if self.horizontal:
            self._button_type = QtGui.QCheckBox
        else:
            self._button_type = QtGui.QRadioButton

        self._enabledButton = self._button_type("Enabled")
        if not self.horizontal:
            self._disabledButton = self._button_type("Disabled")

            buttonGroup = QtGui.QButtonGroup()
            buttonGroup.addButton(self._enabledButton)
            buttonGroup.addButton(self._disabledButton)

        buttonLayout = QtGui.QVBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._enabledButton)
        if not self.horizontal:
            buttonLayout.addWidget(self._disabledButton)

        self.reset_value()
        self.setLayout(buttonLayout)

    def get_value(self):
        return self._enabledButton.isChecked()

    def set_value(self, value):
        self._enabledButton.setChecked(value)
        if not self.horizontal:
            self._disabledButton.setChecked(not value)

class TextFormWidget(QLineEditValidated, FormWidget):
    def __init__(self, form, key, info, settings, horizontal=False, *a, **kw):
        # Qt does not understand the concept of multiple inheritance, since it 
        # is written in C++. Therefore, the QLineEdit must be the first class 
        # we inherit from, otherwise setText (a slot method) does not function.
        # However, we now need to call the FormWidget initializer explicitly, 
        # since it sets up member variables and is not called by QLineEdit.
        # See http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/ 
        # for more details.
        QLineEditValidated.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, settings, horizontal, *a, **kw)
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
            state = validator.validate(text, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return self.info["value"]

        return str(text)

    def set_value(self, value):
        self.setText(self.format_value(value))

    def _format(self):
        self.setText(self.format_value(self.text()))

    def format_value(self, value):
        return str(value) if value is not None else ""

    def is_value_allowed(self):
        return self.hasAcceptableInput()

class FileFormatValidator(QtGui.QRegExpValidator):
    def __init__(self, form_widget, *a, **kw):
        super(FileFormatValidator, self).__init__(*a, **kw)
        self.form_widget = form_widget
        self.settings = self.form_widget.settings
        self.key = self.form_widget.key
        self.info = self.form_widget.info

        regexp = self.settings.make_format_regex(self.info["format"])
        self.setRegExp(QtCore.QRegExp(regexp))

    def validate(self, input, pos):
        if input == "":
            input = None

        try:
            self.settings.check_format(self.key, self.info, input)
            return QtGui.QValidator.Acceptable, pos
        except ValueError:
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
            # Change the value to a short or formatted value. Always prefer the 
            # short value for display unless there is no short version.
            short, full = self.settings.format_file(self.info["format"], value)
            value = short if short is not None else full

        return value

    def get_value(self):
        text = super(FileFormWidget, self).get_value()
        if text == "":
            return None

        # Final format conversion step. We convert back any short formated file 
        # name to the actual file name, if necessary.
        try:
            return self.settings.check_format(self.key, self.info, text)
        except ValueError:
            return self.info["value"]

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
        self.form.resize_widget(self.key)

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
        self._valueWidget = NumericFormWidget(self.form,
                                              "{}-num".format(self.key),
                                              self.info, self.settings,
                                              horizontal=self.horizontal)
        self._slider = None

        self._layout = QtGui.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._valueWidget)

        self.setLayout(self._layout)
        self.setFocusProxy(self._valueWidget)

    def has_slider(self):
        return "min" in self.info and "max" in self.info

    def set_slider(self, slider):
        self._slider = slider
        self._slider.setValue(self._value_to_slider(self.info["value"]))

        self._slider.sliderMoved.connect(self._handle_slider)
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

    def is_value_allowed(self):
        return self._valueWidget.is_value_allowed()

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
    def _get_layout(self):
        if "length" in self.info or self.horizontal:
            return QtGui.QHBoxLayout()

        return QtGui.QVBoxLayout()

    def setup_form(self):
        self._layout = self._get_layout()
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._sub_widgets = []
        self._removeButtons = []
        self._addButton = None

        self._values = self._format_list(self.info["value"])
        self._defaults = self._format_list(self.info["default"])

        if "length" not in self.info:
            self._addButton = QtGui.QToolButton()
            self._addButton.setIcon(QtGui.QIcon("assets/list-add.png"))
            self._addButton.setText("Add item")
            self._addButton.setToolTip("Add another item element to the list")
            self._addButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
            self._addButton.clicked.connect(self._add_to_list)

            self._layout.addWidget(self._addButton)

        self.setLayout(self._layout)

        for _ in range(len(self._values)):
            self._add_to_list()

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
        del sub_info["type"]
        if "length" in sub_info:
            del sub_info["length"]

        if isinstance(sub_info["subtype"], dict):
            sub_info.update(sub_info.pop("subtype"))
        else:
            sub_info["type"] = sub_info.pop("subtype")

        sub_info["value"] = sub_value
        sub_info["default"] = sub_default
        sub_widget = self.form.make_value_widget(self.settings, "{}-{}".format(self.key, position),
                                                 sub_info, horizontal=True)

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
            self._removeButtons.append(removeButton)

            self._fix_tab_order(add=True)
            self.form.resize_widget(self.key)

    def _fix_tab_order(self, add=True):
        if self._addButton is None:
            return

        # Fix tab order in list widgets that can change length
        prev_button = None
        for sub_widget, button in zip(self._sub_widgets, self._removeButtons):
            # Contrary to documentation, Qt does not propagate tab order to the 
            # focus proxy of any widget during manual tab ordering.
            if sub_widget.focusProxy():
                widget = sub_widget.focusProxy()
            else:
                widget = sub_widget

            if prev_button is not None:
                QtGui.QWidget.setTabOrder(prev_button, widget)
            elif add and len(self._sub_widgets) == 1:
                QtGui.QWidget.setTabOrder(self._addButton.previousInFocusChain(), sub_widget)

            QtGui.QWidget.setTabOrder(widget, button)
            prev_button = button

        if prev_button is not None:
            QtGui.QWidget.setTabOrder(prev_button, self._addButton)

    def _remove_item(self, itemLayout, sub_widget, removeButton):
        self._layout.removeItem(itemLayout)
        sub_widget.setParent(None)
        removeButton.setParent(None)
        removeButton.close()
        itemLayout.deleteLater()
        self._layout.invalidate()

        self._sub_widgets.remove(sub_widget)
        self._removeButtons.remove(removeButton)

        self._fix_tab_order(add=False)
        self.form.resize_widget(self.key)

    def get_value(self):
        return [sub_widget.get_value() for sub_widget in self._sub_widgets]

    def set_value(self, value):
        # Replace values in item widgets, add widgets to the list if necessary.
        for position, sub_value in enumerate(value):
            if position >= len(self._sub_widgets):
                self._add_to_list()

            self._sub_widgets[position].set_value(sub_value)

        # Remove item widgets not having a value anymore.
        for _ in xrange(len(value), len(self._sub_widgets)):
            item = self._layout.itemAt(len(value))
            if item.layout():
                self._remove_item(item, item.itemAt(0).widget(), item.itemAt(1).widget())
            else:
                self._layout.removeItem(item)

    def is_value_allowed(self):
        return all(sub_widget.is_value_allowed() for sub_widget in self._sub_widgets)

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

            subWidget = self.form.make_value_widget(self.settings, "{}-{}".format(self.key, key),
                                                    sub_info, horizontal=True)
            formLayout.addRow(keyLabel, subWidget)

            self._sub_widgets[key] = subWidget

        self.setLayout(formLayout)

    def get_value(self):
        return dict((key, subWidget.get_value()) for key, subWidget in self._sub_widgets.iteritems())

    def set_value(self, value):
        for key, subWidget in self._sub_widgets.iteritems():
            subWidget.set_value(value[key])

    def is_value_allowed(self):
        return all(sub_widget.is_value_allowed() for sub_widget in self._sub_widgets.itervalues())

class ChoicesFormWidget(QtGui.QComboBox, FormWidget):
    def __init__(self, form, key, info, settings, horizontal=False, *a, **kw):
        QtGui.QComboBox.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, settings, horizontal, *a, **kw)
        self._types = {
            "int": int,
            "string": str,
            "float": float
        }

        if "replace" in self.info:
            replace = self.info["replace"]
        else:
            replace = ["", ""]

        self._value_table = string.maketrans(*replace)
        self._display_table = string.maketrans(*reversed(replace))

    def add_choices(self, choices):
        if self.count() == 0:
            if "required" in self.info and not self.info["required"]:
                choices[0:0] = [""]

        for i, choice in enumerate(choices):
            self.addItem(str(choice).translate(self._display_table))
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

        return type_cast(str(self.currentText()).translate(self._value_table))

    def set_value(self, value):
        index = self.findText(str(value).translate(self._display_table))
        self.setCurrentIndex(index)
