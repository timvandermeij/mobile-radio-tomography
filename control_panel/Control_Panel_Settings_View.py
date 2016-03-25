import itertools
from functools import partial
from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View
from ..settings import Settings

class Control_Panel_Settings_View(Control_Panel_View):
    def show(self):
        self._add_menu_bar()

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

        defaults = Settings.get_settings(Settings.DEFAULTS_FILE)
        components = sorted(component for component in defaults.iterkeys())
        self._listWidget = QtGui.QListWidget()
        self._listWidget.addItems([defaults[c]["name"] for c in components])
        self._listWidget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)

        self._vboxes = []
        self._components = []

        stackedLayout = QtGui.QStackedLayout()
        for c in components:
            self._components.append(c)

            vbox = QtGui.QVBoxLayout()
            self._vboxes.append(vbox)
            client = QtGui.QWidget()
            client.setLayout(vbox)

            container = QtGui.QScrollArea()
            container.setWidgetResizable(True)
            container.setWidget(client)
            stackedLayout.addWidget(container)

        self._listWidget.currentRowChanged.connect(stackedLayout.setCurrentIndex)
        stackedLayout.currentChanged.connect(lambda i: self._current_changed(i))
        self._current_changed(stackedLayout.currentIndex())

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addWidget(self._listWidget)
        hbox.addLayout(stackedLayout)

    def _format_type(self, info):
        return self._type_names[info["type"]]

    def _format_value(self, info, value=None):
        if value is None:
            value = info["value"]

        if info["type"] == "float":
            value = "{:f}".format(float(value) if value is not None else 0.0)
            value = value.rstrip('0')
            if len(value) == 0 or value[-1] == '.':
                value += '0'

            return value
        if info["type"] == "int":
            return "{:d}".format(int(value) if value is not None else 0)

        return str(value) if value is not None else ""

    def _make_text_widget(self, info):
        valueWidget = QtGui.QLineEdit(self._format_value(info))
        valueWidget.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        return valueWidget

    def _make_numeric_widget(self, info, validator):
        if "min" in info:
            validator.setBottom(info["min"])
        if "max" in info:
            validator.setTop(info["max"])

        valueWidget = self._make_text_widget(info)
        valueWidget.setValidator(validator)
        valueWidget.textChanged.connect(partial(self._validate_widget, valueWidget))

        if "min" in info and "max" in info:
            slider = QtGui.QSlider(QtCore.Qt.Horizontal)
            if info["type"] == "int":
                slider.setRange(info["min"], info["max"])
            else:
                slider.setRange(0,100)

            slider.setValue(self._value_to_slider(slider, info["value"], info))

            slider.valueChanged.connect(partial(self._handle_slider, info, valueWidget, slider))
            valueWidget.textEdited.connect(partial(self._update_slider, info, valueWidget, slider))

            layout = QtGui.QHBoxLayout()
            layout.addWidget(valueWidget)
            layout.addWidget(slider)
            valueWidget = QtGui.QWidget()
            valueWidget.setLayout(layout)

        return valueWidget

    def _slider_to_value(self, slider, value, info):
        minimum = slider.minimum()
        maximum = slider.maximum()
        scale = (float(value) - minimum) / (maximum - minimum)
        return info["min"] + scale * (info["max"] - info["min"])

    def _value_to_slider(self, slider, value, info):
        if value is None:
            value = 0.0

        minimum = slider.minimum()
        maximum = slider.maximum()
        scale = (float(value) - info["min"]) / (info["max"] - info["min"])
        return int(minimum + scale * (maximum - minimum))

    def _handle_slider(self, info, valueWidget, slider, value):
        if info["type"] == "float":
            value = self._slider_to_value(slider, value, info)

        valueWidget.setText(self._format_value(info, value))

    def _update_slider(self, info, valueWidget, slider, text):
        try:
            value = self._value_to_slider(slider, text, info)
        except ValueError:
            return

        slider.setValue(value)

    def _validate_widget(self, valueWidget, text):
        pos = valueWidget.cursorPosition()
        state, newpos = valueWidget.validator().validate(text, pos)
        if state != QtGui.QValidator.Acceptable:
            valueWidget.setStyleSheet("background-color: rgba(255, 0, 0, 60%)");
        else:
            valueWidget.setStyleSheet("background-color: rgba(0, 255, 0, 80%)");

        if newpos != pos:
            valueWidget.setCursorPosition(pos)

    def _format_list(self, info, value):
        if value is None:
            if "length" in info:
                return [None]*info["length"]

            return []

        return value

    def _add_to_list(self, layout, info, sub_value=None, sub_default=None, position=-1):
        sub_info = info.copy()
        sub_info["type"] = sub_info.pop("subtype")
        if "length" in sub_info:
            del sub_info["length"]

        sub_info["value"] = sub_value
        sub_info["default"] = sub_default
        sub_widget = self._make_value_widget(sub_info)

        if "length" in info:
            layout.insertWidget(position, sub_widget)
        else:
            itemLayout = QtGui.QHBoxLayout()

            removeButton = QtGui.QToolButton()
            removeButton.setIcon(QtGui.QIcon("assets/list-remove.png"))
            removeButton.setText("Remove")
            removeButton.setToolTip("Remove this list item element")
            removeButton.setToolButtonStyle(QtCore.Qt.ToolButtonFollowStyle)
            removeButton.clicked.connect(lambda: self._remove_item(layout, itemLayout, sub_widget, removeButton))

            itemLayout.addWidget(sub_widget)
            itemLayout.addWidget(removeButton)
            layout.insertLayout(position, itemLayout)

    def _remove_item(self, layout, itemLayout, sub_widget, removeButton):
        layout.removeItem(itemLayout)
        sub_widget.setParent(None)
        removeButton.setParent(None)
        removeButton.close()
        itemLayout.deleteLater()
        layout.invalidate()

    def _fix_label_alignment(self, valueLabel, valueWidget):
        # Fix up vertical alignment for layout value fields
        if valueWidget.layout() is not None:
            valueLabel.setAlignment(QtCore.Qt.AlignBottom)

    def _make_value_widget(self, info):
        if info["type"] == "bool":
            enabledButton = QtGui.QRadioButton("Enabled")
            disabledButton = QtGui.QRadioButton("Disabled")

            enabledButton.setChecked(info["value"])
            disabledButton.setChecked(not info["value"])

            buttonGroup = QtGui.QButtonGroup()
            buttonGroup.addButton(enabledButton)
            buttonGroup.addButton(disabledButton)

            buttonLayout = QtGui.QVBoxLayout()
            buttonLayout.setSpacing(0)
            buttonLayout.addWidget(enabledButton)
            buttonLayout.addWidget(disabledButton)

            valueWidget = QtGui.QWidget()
            valueWidget.setLayout(buttonLayout)
        elif info["type"] == "float":
            validator = QtGui.QDoubleValidator()
            validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
            valueWidget = self._make_numeric_widget(info, validator)
        elif info["type"] == "int":
            validator = QtGui.QIntValidator()
            valueWidget = self._make_numeric_widget(info, validator)
        elif info["type"] in ("list", "tuple"):
            if "length" in info:
                layout = QtGui.QHBoxLayout()
            else:
                layout = QtGui.QVBoxLayout()

            value = self._format_list(info, info["value"])
            default = self._format_list(info, info["default"])
            for sub_value, sub_default in itertools.izip_longest(value, default):
                self._add_to_list(layout, info, sub_value, sub_default)

            if "length" not in info:
                addButton = QtGui.QToolButton()
                addButton.setIcon(QtGui.QIcon("assets/list-add.png"))
                addButton.setText("Add item")
                addButton.setToolTip("Add another item element to the list")
                addButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
                addButton.clicked.connect(lambda: self._add_to_list(layout, info, position=layout.count()-1))
                layout.addWidget(addButton)

            valueWidget = QtGui.QWidget()
            valueWidget.setLayout(layout)
        elif info["type"] == "dict":
            formLayout = QtGui.QFormLayout()
            for key, value_info in info["dictinfo"].iteritems():
                sub_info = value_info.copy()
                if info["default"] is not None:
                    sub_info["value"] = info["value"][key]
                    sub_info["default"] = info["default"][key]
                else:
                    sub_info.update({"value": None, "default": None})

                key_text = "{} ({}):".format(key, self._format_type(sub_info))
                keyLabel = QtGui.QLabel(key_text)
                subWidget = self._make_value_widget(sub_info)
                self._fix_label_alignment(keyLabel, subWidget)
                formLayout.addRow(keyLabel, subWidget)

            valueWidget = QtGui.QWidget()
            valueWidget.setLayout(formLayout)
        else:
            choices = self._controller.arguments.get_choices(info)
            if choices is not None:
                valueWidget = QtGui.QComboBox()
                if "required" in info and not info["required"]:
                    choices[0:0] = [""]
                for i, choice in enumerate(choices):
                    valueWidget.addItem(choice)
                    if choice == info["value"]:
                        valueWidget.setCurrentIndex(i)
            else:
                valueWidget = self._make_text_widget(info)

        return valueWidget

    def _current_changed(self, index):
        # Lazily load the stacked widget.
        if self._vboxes[index].isEmpty():
            component = self._components[index]
            settings = self._controller.arguments.get_settings(component)

            titleLabel = QtGui.QLabel("{} ({})".format(settings.name, component))
            titleLabel.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
            titleLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
            titleLabel.setStyleSheet("QLabel { font-size: 24px; background: white }")
            titleLabel.setWordWrap(True)
            self._vboxes[index].addWidget(titleLabel)

            if settings.parent is not None:
                parentButton = QtGui.QCommandLinkButton(settings.parent.name, "Go to parent ({})".format(settings.parent.component_name))
                parentButton.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
                parentButton.clicked.connect(lambda: self._listWidget.setCurrentRow(self._components.index(settings.parent.component_name)))

                self._vboxes[index].addWidget(parentButton)

            first = True
            for key, info in settings.get_info():
                if first:
                    first = False
                else:
                    line = QtGui.QFrame()
                    line.setFrameShape(QtGui.QFrame.HLine)
                    line.setFrameShadow(QtGui.QFrame.Sunken)
                    self._vboxes[index].addWidget(line)

                formLayout = QtGui.QFormLayout()
                formLayout.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)

                typeLabel = QtGui.QLabel(self._format_type(info))
                formLayout.addRow("Type:", typeLabel)

                descriptionLabel = QtGui.QLabel("Description:")
                descriptionLabel.setAlignment(QtCore.Qt.AlignTop)
                description = QtGui.QLabel(self._controller.arguments.get_help(key, info))
                description.setWordWrap(True)
                formLayout.addRow(descriptionLabel, description)

                valueWidget = self._make_value_widget(info)

                valueLabel = QtGui.QLabel("Value:")
                self._fix_label_alignment(valueLabel, valueWidget)
                formLayout.addRow(valueLabel, valueWidget)

                groupBox = QtGui.QGroupBox(key)
                groupBox.setLayout(formLayout)
                self._vboxes[index].addWidget(groupBox)

