import sys
from __init__ import __package__
from dashboard.Dashboard import Dashboard
from PyQt4 import QtGui

def main(argv):
    app = QtGui.QApplication(argv)
    dashboard = Dashboard()
    dashboard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(sys.argv[1:])
