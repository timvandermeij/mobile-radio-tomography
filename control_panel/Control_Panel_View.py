from PyQt4 import QtCore

class Control_Panel_View_Name(object):
    LOADING = 1
    RECONSTRUCTION = 2
    WAYPOINTS = 3

class Control_Panel_View(object):
    def __init__(self, controller):
        """
        Initialize the control panel view.
        """

        self._controller = controller

    def clear(self):
        """
        Clear the view, thereby deleting any existing widgets.
        """

        layout = self._controller.central_widget.layout()

        # Delete all widgets in the layout.
        if layout is not None:
            for item in reversed(range(layout.count())):
                widget = layout.itemAt(item).widget()
                if widget is not None:
                    widget.setParent(None)

        # Delete the layout itself.
        QtCore.QObjectCleanupHandler().add(layout)
