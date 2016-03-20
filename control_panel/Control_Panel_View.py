from PyQt4 import QtCore, QtGui

class Control_Panel_View_Name(object):
    DEVICES = 1
    LOADING = 2
    RECONSTRUCTION = 3
    WAYPOINTS = 4

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

        Subclasses can extend this to add more custom menus and actions to
        the menu bar. If they do so, then they must extend the `clear` method
        with the following code to clear the entire menu bar:

        if self._controller.window._menu_bar is not None:
            self._controller.window._menu_bar.clear()
            self._controller.window._menu_bar = None
        """

        self._controller.add_menu_bar()
