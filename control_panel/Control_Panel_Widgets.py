import itertools
import os
import re
from PyQt4 import QtCore, QtGui

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

            valueWidget = self.make_value_widget(key, info)

            valueLabel = QtGui.QLabel("Value:")
            formLayout.addRow(valueLabel, valueWidget)

            groupBox = QtGui.QGroupBox(key)
            groupBox.setLayout(formLayout)
            layout.addWidget(groupBox)

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

    def _trigger_parent_clicked(self):
        self.parentClicked.emit(self._settings.parent.component_name)

class FormWidget(QtGui.QWidget):
    def __init__(self, form, key, info, *a, **kw):
        super(FormWidget, self).__init__(*a, **kw)
        self.form = form
        self.key = key
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
    def __init__(self, form, key, info, *a, **kw):
        # Qt does not understand the concept of multiple inheritance, since it 
        # is written in C++. Therefore, the QLineEdit must be the first class 
        # we inherit from, otherwise setText (a slot method) does not function.
        # However, we now need to call the FormWidget initializer explicitly, 
        # since it sets up member variables and is not called by QLineEdit.
        # See http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/ 
        # for more details.
        QtGui.QLineEdit.__init__(self, *a, **kw)
        FormWidget.__init__(self, form, key, info, *a, **kw)

    def setup_form(self):
        self.reset_value()
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        self.editingFinished.connect(self._format)

    def setValidator(self, v):
        super(TextFormWidget, self).setValidator(v)
        validator = self.validator()
        if validator is not None:
            self.textChanged.connect(self._validate)
        else:
            self.textChanged.disconnect(self._validate)

    def reset_value(self):
        self.setText(self.format_value(self.info["value"]))

    def _format(self):
        self.setText(self.format_value(self.text()))

    def format_value(self, value):
        return str(value) if value is not None else ""

    def _update_stylesheet(self, color):
        decl = "background-color: "
        styleSheet = str(self.styleSheet())
        newSheet, count = re.subn("({})(.*)(;)".format(decl), r"\1{}\3".format(color), styleSheet)
        if count == 0:
            newSheet = styleSheet + decl + color + ";"

        self.setStyleSheet(newSheet)

    def _validate(self, text):
        pos = self.cursorPosition()
        state, newpos = self.validator().validate(text, pos)
        if state != QtGui.QValidator.Acceptable:
            color = "#fd6464"
        else:
            color = "#32fe32"

        self._update_stylesheet(color)

        if newpos != pos:
            self.setCursorPosition(pos)

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

    def _open_file(self):
        if "format" in self.info:
            directory, file_format = os.path.split(self.info["format"])
            file_type = os.path.splitext(file_format)[1]
            file_filter = "{} files (*{})".format(file_type[1:].upper(), file_type)
        else:
            directory = ""
            file_filter = ""

        work_dir = os.getcwd() + "/"
        file_name = QtGui.QFileDialog.getOpenFileName(self, "Select file",
                                                      work_dir + directory,
                                                      file_filter)

        if file_name == "":
            return

        file_name = os.path.relpath(str(file_name), work_dir)

        self.setText(self.format_value(file_name))

    def resizeEvent(self, event):
        self.openButton.resizeEvent(event)

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

    def set_formatter(self, formatter):
        self._formatter = formatter
        self.reset_value()

    def format_value(self, value):
        if self._formatter:
            return self._formatter(value)

        return super(NumericFormWidget, self).format_value(value)

class NumericSliderFormWidget(FormWidget):
    def setup_form(self):
        self._valueWidget = NumericFormWidget(self.form, "{}-num".format(self.key), self.info)

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
        if position == -1:
            position = self._layout.count()

        sub_info = self.info.copy()
        sub_info["type"] = sub_info.pop("subtype")
        if "length" in sub_info:
            del sub_info["length"]

        sub_info["value"] = sub_value
        sub_info["default"] = sub_default
        sub_widget = self.form.make_value_widget("{}-{}".format(self.key, position), sub_info)

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
            subWidget = self.form.make_value_widget("{}-{}".format(self.key, key), sub_info)
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
