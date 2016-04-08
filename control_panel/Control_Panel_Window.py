from PyQt4 import QtGui
from Control_Panel_Controller import Control_Panel_Controller, Control_Panel_View_Name

class Control_Panel_Window(QtGui.QMainWindow):
    def __init__(self, app):
        """
        Initialize the control panel window.
        """

        super(Control_Panel_Window, self).__init__()

        self._menu_bar = None
        self._toolbar = None

        # Set the dimensions, title and icon of the window.
        self.setGeometry(0, 0, 900, 700)
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
        self.controller = Control_Panel_Controller(app, central_widget, self)

        # Show the loading view (default).
        self.controller.show_view(Control_Panel_View_Name.LOADING)

    def closeEvent(self, event):
        """
        Close the application and kill running threads and serial connections.
        """

        self.controller.xbee.deactivate()
        self.controller.thread_manager.destroy()
        self.controller.usb_manager.clear()

        event.accept()
