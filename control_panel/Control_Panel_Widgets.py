import re
from PyQt4 import QtCore, QtGui

class QToolBarFocus(QtGui.QToolBar):
    def __init__(self, app, *a, **kw):
        super(QToolBarFocus, self).__init__(*a, **kw)
        self._app = app
        self._focused = False

        self._app.focusChanged.connect(self._global_focus_changed)
        self._is_connected = True

    def hideEvent(self, event):
        if self._is_connected:
            self._app.focusChanged.disconnect(self._global_focus_changed)
            self._is_connected = False

        super(QToolBarFocus, self).hideEvent(event)

    def _global_focus_changed(self, old, now):
        if now is None:
            self._set_focus(False)
            return

        barRect = QtCore.QRect(self.mapToGlobal(QtCore.QPoint(0, 0)),
                               self.mapToGlobal(QtCore.QPoint(self.width(),
                                                              self.height())))
        nowRect = QtCore.QRect(now.mapToGlobal(QtCore.QPoint(0, 0)),
                               now.mapToGlobal(QtCore.QPoint(now.width(),
                                                             now.height())))

        self._set_focus(barRect.contains(nowRect))

    def _set_focus(self, focused):
        wasFocused = self._focused
        self._focused = focused
        if wasFocused and not self._focused:
            self.layout().setExpanded(False)

    def event(self, event):
        if event.type() == QtCore.QEvent.Leave and self._focused:
            # Do not pass the leave event to the normal toolbar event handler, 
            # but to the QWidget base class, so that the toolbar remains 
            # expanded when it is focused.
            return QtGui.QWidget.event(self, event)

        return super(QToolBarFocus, self).event(event)

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

class QLineEditValidated(QtGui.QLineEdit):
    def __init__(self, *a, **kw):
        QtGui.QLineEdit.__init__(self, *a, **kw)
        self._background_color = ""
        self._validator_state = None

    def setValidator(self, v):
        super(QLineEditValidated, self).setValidator(v)
        validator = self.validator()
        self._validator_state = None
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

    def get_validator_state(self):
        if self._validator_state is None:
            validator = self.validator()
            if validator is not None:
                self._validate(self.text())
            else:
                self._validator_state = QtGui.QValidator.Acceptable

        return self._validator_state

    def set_validator_state(self, state):
        self._validator_state = state
        if state != QtGui.QValidator.Acceptable:
            color = "#FA6969"
        else:
            color = "#8BD672"

        self.set_background_color(color)

    def _validate(self, text):
        pos = self.cursorPosition()
        state, newpos = self.validator().validate(text, pos)
        self.set_validator_state(state)

        if newpos != pos:
            self.setCursorPosition(pos)

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
