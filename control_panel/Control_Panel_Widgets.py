import itertools
from PyQt4 import QtCore, QtGui

# Ported from https://github.com/Frodox/qt-line-edit-with-clear-button
# Qt5's QLineEdit has this built in via the clearButtonEnabled.
# We emulate its behavior here.
class QLineEditClear(QtGui.QLineEdit):
    def __init__(self, *a, **kw):
        super(QLineEditClear, self).__init__(*a, **kw)

        self.clearButton = QtGui.QToolButton(self)
        self.clearButton.setIcon(QtGui.QIcon("assets/edit-clear.png"))
        self.clearButton.setCursor(QtCore.Qt.ArrowCursor)
        self.clearButton.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        self.clearButton.hide()

        self.clearButton.clicked.connect(self.clear)
        self.textChanged.connect(self.updateCloseButton)

        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        width = self.clearButton.sizeHint().width() + frameWidth + 1
        self.setStyleSheet("QLineEdit {{ padding-right: {}px; }}".format(width))

        msz = self.minimumSizeHint()
        # Source assumed square icon here, but we do not.
        fill = frameWidth * 2 + 2
        self.setMinimumSize(max(msz.width(), self.clearButton.width() + fill),
                            max(msz.height(), self.clearButton.height() + fill))

    def resizeEvent(self, event):
        size = self.clearButton.sizeHint()
        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        self.clearButton.move(self.rect().right() - frameWidth - size.width(),
                              (self.rect().bottom() + 1 - size.height())/2)

    def updateCloseButton(self, text):
        self.clearButton.setVisible(not text.isEmpty())

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
            "file": TextFormWidget,
            "class": TextFormWidget, # Unless "choices" is supplied
            "list": ListFormWidget,
            "tuple": ListFormWidget,
            "dict": DictFormWidget
        }

        self._component = component
        self._arguments = arguments
        self._settings = self._arguments.get_settings(self._component)

        self._widgets = {}

        layout = QtGui.QVBoxLayout()

        titleLabel = QtGui.QLabel("{} ({})".format(self._settings.name, self._component))
        titleLabel.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        titleLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        titleLabel.setStyleSheet("QLabel { font-size: 24px; background: white }")
        titleLabel.setWordWrap(True)

        layout.addWidget(titleLabel)

        if self._settings.parent is not None:
            parentButton = QtGui.QCommandLinkButton(self._settings.parent.name, "Go to parent ({})".format(self._settings.parent.component_name))
            parentButton.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
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
            description.setWordWrap(True)
            formLayout.addRow(descriptionLabel, description)

            valueWidget = self.make_value_widget(info)

            valueLabel = QtGui.QLabel("Value:")
            formLayout.addRow(valueLabel, valueWidget)

            groupBox = QtGui.QGroupBox(key)
            groupBox.setLayout(formLayout)
            layout.addWidget(groupBox)

            self._widgets[key] = groupBox

        self.setLayout(layout)

    def get_setting_widget(self, key):
        if key not in self._widgets:
            raise KeyError("Setting '{}' in component '{}' does not have a widget.".format(key, self._component))

        return self._widgets[key]

    def format_type(self, info):
        return self._type_names[info["type"]]

    def make_value_widget(self, info):
        choices = self._arguments.get_choices(info)
        if choices is not None:
            widget = ChoicesFormWidget(self, info)
            widget.add_choices(choices)
        else:
            widget_type = self._type_widgets[info["type"]]
            widget = widget_type(self, info)

        return widget

    def _trigger_parent_clicked(self):
        self.parentClicked.emit(self._settings.parent.component_name)

class FormWidget(QtGui.QWidget):
    def __init__(self, form, info, *a, **kw):
        super(FormWidget, self).__init__(*a, **kw)
        self.form = form
        self.info = info
        self.setup_form()

    def setup_form(self):
        pass

    def get_value(self):
        raise NotImplementedError("Subclasses must implement `get_value`")

    def is_value_changed(self):
        raise NotImplementedError("Subclasses must implement `is_value_changed`")

class BooleanFormWidget(FormWidget):
    def setup_form(self):
        enabledButton = QtGui.QRadioButton("Enabled")
        disabledButton = QtGui.QRadioButton("Disabled")

        enabledButton.setChecked(self.info["value"])
        disabledButton.setChecked(not self.info["value"])

        buttonGroup = QtGui.QButtonGroup()
        buttonGroup.addButton(enabledButton)
        buttonGroup.addButton(disabledButton)

        buttonLayout = QtGui.QVBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(enabledButton)
        buttonLayout.addWidget(disabledButton)

        self.setLayout(buttonLayout)

class TextFormWidget(QtGui.QLineEdit, FormWidget):
    def __init__(self, form, info, *a, **kw):
        # Qt does not understand the concept of multiple inheritance, since it 
        # is written in C++. Therefore, the QLineEdit must be the first class 
        # we inherit from, otherwise setText (a slot method) does not function.
        # However, we now need to call the FormWidget initializer explicitly, 
        # since it sets up member variables and is not called by QLineEdit.
        # See http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/ 
        # for more details.
        QtGui.QLineEdit.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, info, *a, **kw)

    def setup_form(self):
        self.reset_value()
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)

    def reset_value(self):
        self.setText(self.format_value(self.info["value"]))

    def format_value(self, value):
        return str(value) if value is not None else ""

class NumericFormWidget(TextFormWidget):
    def setup_form(self):
        self._formatter = None
        super(NumericFormWidget, self).setup_form()

    def setValidator(self, v):
        super(NumericFormWidget, self).setValidator(v)

        validator = self.validator()
        if validator is not None:
            if "min" in self.info:
                validator.setBottom(self.info["min"])
            if "max" in self.info:
                validator.setTop(self.info["max"])

            self.textChanged.connect(self._validate)
        else:
            self.textChanged.disconnect(self._validate)

    def set_formatter(self, formatter):
        self._formatter = formatter
        self.reset_value()

    def format_value(self, value):
        if self._formatter:
            return self._formatter(value)

        return super(NumericFormWidget, self).format_value(value)

    def _validate(self, text):
        pos = self.cursorPosition()
        state, newpos = self.validator().validate(text, pos)
        if state != QtGui.QValidator.Acceptable:
            self.setStyleSheet("background-color: rgba(255, 0, 0, 60%)")
        else:
            self.setStyleSheet("background-color: rgba(0, 255, 0, 80%)")

        if newpos != pos:
            self.setCursorPosition(pos)

class NumericSliderFormWidget(FormWidget):
    def setup_form(self):
        self._valueWidget = NumericFormWidget(self.form, self.info)

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

        value = self._format_list(self.info["value"])
        default = self._format_list(self.info["default"])
        for sub_value, sub_default in itertools.izip_longest(value, default):
            self._add_to_list(sub_value, sub_default)

        if "length" not in self.info:
            addButton = QtGui.QToolButton()
            addButton.setIcon(QtGui.QIcon("assets/list-add.png"))
            addButton.setText("Add item")
            addButton.setToolTip("Add another item element to the list")
            addButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
            addButton.clicked.connect(lambda: self._add_to_list(position=self._layout.count()-1))
            self._layout.addWidget(addButton)

        self.setLayout(self._layout)

    def _format_list(self, value):
        if value is None:
            if "length" in self.info:
                return [None]*self.info["length"]

            return []

        return value

    def _add_to_list(self, sub_value=None, sub_default=None, position=-1):
        sub_info = self.info.copy()
        sub_info["type"] = sub_info.pop("subtype")
        if "length" in sub_info:
            del sub_info["length"]

        sub_info["value"] = sub_value
        sub_info["default"] = sub_default
        sub_widget = self.form.make_value_widget(sub_info)

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

class DictFormWidget(FormWidget):
    def setup_form(self):
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
            subWidget = self.form.make_value_widget(sub_info)
            formLayout.addRow(keyLabel, subWidget)

        self.setLayout(formLayout)

class ChoicesFormWidget(QtGui.QComboBox, FormWidget):
    __init__ = FormWidget.__init__

    def add_choices(self, choices):
        if self.count() == 0:
            if "required" in self.info and not self.info["required"]:
                choices[0:0] = [""]

        for i, choice in enumerate(choices):
            self.addItem(str(choice))
            if choice == self.info["value"]:
                self.setCurrentIndex(i)
