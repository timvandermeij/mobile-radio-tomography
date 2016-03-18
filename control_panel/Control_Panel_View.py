from PyQt4 import QtCore, QtGui

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

    def clear(self, layout=None):
        """
        Clear the view, thereby deleting any existing widgets.
        """

        menu_bar = self._controller.window._menu_bar
        if menu_bar is not None:
            menu_bar.hide()

        toolbar = self._controller.window._toolbar
        if toolbar is not None:
            self._controller.window.removeToolBar(toolbar)
            self._controller.window._toolbar = None

        if layout is not None:
            for index in reversed(range(layout.count())):
                item = layout.itemAt(index)

                if isinstance(item, QtGui.QWidgetItem):
                    item.widget().close()
                else:
                    self.clear(item.layout())

            # Delete the layout itself.
            QtCore.QObjectCleanupHandler().add(layout)

    def _add_menu_bar(self):
        """
        Create a menu bar for the window.
        """

        if self._controller.window._menu_bar is not None:
            self._controller.window._menu_bar.show()
            return

        self._controller.window._menu_bar = self._controller.window.menuBar()

        reconstruction_action = QtGui.QAction("Reconstruction", self._controller.window)
        reconstruction_action.triggered.connect(
            lambda: self._controller.show_view(Control_Panel_View_Name.RECONSTRUCTION)
        )

        waypoints_action = QtGui.QAction("Waypoints", self._controller.window)
        waypoints_action.triggered.connect(
            lambda: self._controller.show_view(Control_Panel_View_Name.WAYPOINTS)
        )

        view_menu = self._controller.window._menu_bar.addMenu("View")
        view_menu.addAction(reconstruction_action)
        view_menu.addAction(waypoints_action)
