import os
import string
from functools import partial
from PyQt4 import QtCore, QtGui
from Control_Panel_Widgets import QLineEditValidated, QLineEditToolButton

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
        return str(self.text())

    def set_value(self, value):
        self.setText(self.format_value(value))

    def _format(self):
        self.setText(self.format_value(self.text()))

    def format_value(self, value):
        return str(value) if value is not None else ""

    def is_value_allowed(self):
        if self.get_validator_state() == QtGui.QValidator.Acceptable:
            return True

        return self.is_value_default()

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

    def add_action(self, action):
        self._actions.append(action)

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

        if "inf" in self.info and self.info["inf"]:
            inf_actions = [
                ("infinity", "inf", "max"), ("negative infinity", "-inf", "min")
            ]
            for name, value, limit in inf_actions:
                if limit not in self.info:
                    inf_action = QtGui.QAction("Set to {}".format(name), self)
                    inf_action.triggered.connect(partial(self._set_inf, value))
                    self._actions.append(inf_action)
                    self._valueWidget.add_action(inf_action)

    def _set_inf(self, value):
        self.set_value(value)
        self._valueWidget.set_validator_state(QtGui.QValidator.Acceptable)

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
