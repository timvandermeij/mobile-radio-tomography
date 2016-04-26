import os
import re
from PyQt4 import QtCore, QtGui
from Control_Panel_Widgets import QLineEditToolButton

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

        first = True
        for key, info in self._settings.get_info():
            valueWidget = self.make_value_widget(key, info)

            self._widgets[key] = self._add_group_box(key, info, valueWidget, first)
            self._value_widgets[key] = valueWidget
            first = False

        self.setLayout(self._layout)

    def isHorizontal(self):
        """
        Check whether the widget's form items should be laid out in a most
        horizontal way possible.
        """

        return False

    def _create_layout(self):
        if not self._horizontal_mode:
            self._layout = QtGui.QVBoxLayout()

            self._add_title_label()
            self._add_parent_button()
        else:
            self._layout = QtGui.QHBoxLayout()

    def _add_title_label(self):
        titleLabel = QtGui.QLabel("{} ({})".format(self._settings.name, self._component))
        titleLabel.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        titleLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        titleLabel.setStyleSheet("QLabel { font-size: 24px; background: white }")
        titleLabel.setWordWrap(True)

        self._layout.addWidget(titleLabel)

    def _add_parent_button(self):
        if self._settings.parent is not None:
            parentButton = QtGui.QCommandLinkButton(self._settings.parent.name, "Go to parent ({})".format(self._settings.parent.component_name))
            policy = parentButton.sizePolicy()
            policy.setVerticalPolicy(QtGui.QSizePolicy.Fixed)
            parentButton.setSizePolicy(policy)
            parentButton.clicked.connect(self._trigger_parent_clicked)

            self._layout.addWidget(parentButton)

    def _add_group_box(self, key, info, valueWidget, first=False):
        if not first:
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

    def format_type(self, info):
        """
        Retrieve a human-readable version for the settings type in the settings
        information dictionary `info`.
        """

        return self._type_names[info["type"]]

    def make_value_widget(self, key, info, horizontal=None):
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
            widget = ChoicesFormWidget(self, key, info, horizontal)
            widget.add_choices(choices)
        else:
            widget_type = self._type_widgets[info["type"]]
            widget = widget_type(self, key, info, horizontal)

        return widget

    def get_values(self):
        """
        Retrieve the current values from the input widgets that have changed
        from the default.

        The returned dictionary contains the settings keys and the changed
        values.
        """

        values = {}
        for key, widget in self._value_widgets.iteritems():
            if not widget.is_value_default():
                values[key] = widget.get_value()

        return values

    def _trigger_parent_clicked(self):
        self.parentClicked.emit(self._settings.parent.component_name)

class SettingsToolbarWidget(SettingsWidget):
    def isHorizontal(self):
        return True

    def _add_group_box(self, key, info, valueWidget, first=False):
        labelWidget = QtGui.QLabel("{}:".format(info["short"] if "short" in info else key))
        labelWidget.setToolTip(self._arguments.get_help(key, info))
        self._layout.addWidget(labelWidget)
        self._layout.addWidget(valueWidget)

        return valueWidget

class FormWidget(QtGui.QWidget):
    def __init__(self, form, key, info, horizontal=False, *a, **kw):
        super(FormWidget, self).__init__(*a, **kw)
        self.form = form
        self.key = key
        self.info = info
        self.horizontal = horizontal

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
        if self.horizontal:
            self._enabledButton = QtGui.QCheckBox("Enabled")
        else:
            self._enabledButton = QtGui.QRadioButton("Enabled")
            self._disabledButton = QtGui.QRadioButton("Disabled")

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
    def __init__(self, form, key, info, horizontal=False, *a, **kw):
        # Qt does not understand the concept of multiple inheritance, since it 
        # is written in C++. Therefore, the QLineEdit must be the first class 
        # we inherit from, otherwise setText (a slot method) does not function.
        # However, we now need to call the FormWidget initializer explicitly, 
        # since it sets up member variables and is not called by QLineEdit.
        # See http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/ 
        # for more details.
        QLineEditValidated.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, horizontal, *a, **kw)
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
        if "length" in self.info or self.horizontal:
            self._layout = QtGui.QHBoxLayout()
        else:
            self._layout = QtGui.QVBoxLayout()

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

        for i in range(len(self._values)):
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
        sub_widget = self.form.make_value_widget("{}-{}".format(self.key, position), sub_info, horizontal=True)

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

    def _fix_tab_order(self, add=True):
        if self._addButton is None:
            return

        # Fix tab order in list widgets that can change length
        prev_button = None
        for sub_widget, button, i in zip(self._sub_widgets, self._removeButtons, range(len(self._sub_widgets))):
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

            subWidget = self.form.make_value_widget("{}-{}".format(self.key, key), sub_info, horizontal=True)
            formLayout.addRow(keyLabel, subWidget)

            self._sub_widgets[key] = subWidget

        self.setLayout(formLayout)

    def get_value(self):
        return dict((key, subWidget.get_value()) for key, subWidget in self._sub_widgets.iteritems())

    def set_value(self, value):
        for key, subWidget in self._sub_widgets.iteritems():
            subWidget.set_value(value[key])

class ChoicesFormWidget(QtGui.QComboBox, FormWidget):
    def __init__(self, form, key, info, horizontal=False, *a, **kw):
        QtGui.QLineEdit.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, horizontal, *a, **kw)
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
