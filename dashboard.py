import sys
from __init__ import __package__
from dashboard.Dashboard import Dashboard
from settings import Settings
from PyQt4 import QtGui

def main(argv):
    app = QtGui.QApplication(argv)
    settings = Settings("settings.json", "dashboard")
    dashboard = Dashboard(settings)
    dashboard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(sys.argv[1:])
