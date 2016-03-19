import sys
from __init__ import __package__
from control_panel.Control_Panel_Window import Control_Panel_Window
from PyQt4 import QtGui

def main(argv):
    app = QtGui.QApplication(argv)
    control_panel_window = Control_Panel_Window(app)
    control_panel_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(sys.argv[1:])
