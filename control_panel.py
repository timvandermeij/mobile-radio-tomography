import sys
from __init__ import __package__
from control_panel.Control_Panel import Control_Panel
from PyQt4 import QtGui

def main(argv):
    app = QtGui.QApplication(argv)
    control_panel = Control_Panel()
    control_panel.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(sys.argv[1:])
