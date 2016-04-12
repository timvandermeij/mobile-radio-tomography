from PyQt4 import QtCore, QtGui

class Control_Panel_View_Name(object):
    LOADING = 0
    DEVICES = 1
    PLANNING = 2
    RECONSTRUCTION = 3
    WAYPOINTS = 4
    SETTINGS = 5

class Control_Panel_View(object):
    def __init__(self, controller, settings):
        """
        Initialize the control panel view.
        """

        self._controller = controller
        self._settings = settings

    def load(self, data):
        """
        Load any cached information of the view to reinitialize it.
        """

        pass

    def save(self):
        """
        Return information that can be cached when the view is being closed.
        """

        return {}

    def show(self):
        raise NotImplementedError("Subclasses must implement `show()`")

    def clear(self, layout=None):
        """
        Clear the view, thereby deleting any existing widgets.
        """

        menu_bar = self._controller.window._menu_bar
        if menu_bar is not None:
            menu_bar.hide()

        for toolbar in self._controller.window._toolbars:
            self._controller.window.removeToolBar(toolbar)

        self._controller.window._toolbars = []

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
