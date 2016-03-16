from PyQt4 import QtGui
from Control_Panel_Controller import Control_Panel_Controller

class Control_Panel_Window(QtGui.QMainWindow):
    def __init__(self):
        """
        Initialize the control panel window.
        """

        super(Control_Panel_Window, self).__init__()

        # Set the dimensions, title and icon of the window.
        self.setGeometry(0, 0, 800, 600)
        self.setWindowTitle("Mobile radio tomography")
        self.setWindowIcon(QtGui.QIcon("assets/mobile-radio-tomography.png"))

        # Center the window.
        resolution = QtGui.QDesktopWidget().screenGeometry()
        frame_size = self.frameSize()
        self.move(resolution.width() / 2 - frame_size.width() / 2,
                  resolution.height() / 2 - frame_size.height() / 2)

        # Create a central widget.
        central_widget = QtGui.QWidget()
        self.setCentralWidget(central_widget)

        # Create a controller.
        controller = Control_Panel_Controller(central_widget, self)
