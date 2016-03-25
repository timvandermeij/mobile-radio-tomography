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
