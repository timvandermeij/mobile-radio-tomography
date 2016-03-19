from collections import OrderedDict
from functools import partial
import sys
import traceback
from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View_Name
from Control_Panel_Loading_View import Control_Panel_Loading_View
from Control_Panel_Reconstruction_View import Control_Panel_Reconstruction_View
from Control_Panel_Waypoints_View import Control_Panel_Waypoints_View
from ..core.Thread_Manager import Thread_Manager
from ..core.USB_Manager import USB_Manager
from ..settings import Arguments
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator
from ..zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical

class Control_Panel_Controller(object):
    def __init__(self, app, central_widget, window):
        """
        Initialize the control panel controller.
        """

        self.app = app
        self.central_widget = central_widget
        self.window = window
        self._current_view = None
        self._current_view_name = None
        self._view_actions = {}

        # Create arguments (for obtaining various settings in views)
        # and a USB manager (for checking insertion of XBee devices).
        # Initialize the XBee sensor for use by specific views.
        self.arguments = Arguments("settings.json", sys.argv[1:])
        self.thread_manager = Thread_Manager()
        self.usb_manager = USB_Manager()
        self.usb_manager.index()

        settings = self.arguments.get_settings("control_panel")
        if settings.get("controller_xbee_simulation"):
            xbee_class = XBee_Sensor_Simulator
        else:
            xbee_class = XBee_Sensor_Physical

        self.xbee = xbee_class(self.arguments, self.thread_manager,
                               self.usb_manager, self._get_location,
                               self._receive, self._location_valid)

        self._packet_callbacks = {}

        self.arguments.check_help()

    def _get_location(self):
        return (0, 0)

    def _receive(self, packet):
        specification = packet.get("specification")
        if specification in self._packet_callbacks:
            callback = self._packet_callbacks[specification]
            callback(packet)

    def _location_valid(self, other_valid=None):
        return False

    def add_packet_callback(self, specification, callback):
        if not hasattr(callback, "__call__"):
            raise TypeError("The provided callback is not callable.")

        self._packet_callbacks[specification] = callback

    def remove_packet_callback(self, specification):
        if specification in self._packet_callbacks:
            del self._packet_callbacks[specification]

    def show_view(self, name):
        """
        Show a new view, identified by `name`, and clear the current view.
        """

        # If we select the current view, then we do not need to change views.
        if self._current_view_name == name:
            self._view_actions[name].setChecked(True)
            return

        if self._current_view is not None:
            self._current_view.clear(self.central_widget.layout())

        if self._current_view_name in self._view_actions:
            self._view_actions[self._current_view_name].setChecked(False)
        if name in self._view_actions:
            self._view_actions[name].setChecked(True)

        views = {
            Control_Panel_View_Name.LOADING: Control_Panel_Loading_View,
            Control_Panel_View_Name.RECONSTRUCTION: Control_Panel_Reconstruction_View,
            Control_Panel_View_Name.WAYPOINTS: Control_Panel_Waypoints_View
        }

        try:
            if name not in views:
                raise ValueError("Unknown view name specified.")

            view = views[name](self)
            self._current_view = view
            self._current_view_name = name
            view.show()
        except Exception as e:
            QtGui.QMessageBox.critical(self.central_widget, "Internal error",
                                       traceback.format_exc() + "\nThe application will now exit.")
            self.window.close()
            sys.exit(1)

    def add_menu_bar(self):
        """
        Create a menu bar for the window.
        """

        if self.window._menu_bar is not None:
            self.window._menu_bar.show()
            return

        self.window._menu_bar = self.window.menuBar()

        # Views that are visible in the menu and their action labels.
        view_names = OrderedDict([
            (Control_Panel_View_Name.RECONSTRUCTION, "Reconstruction"),
            (Control_Panel_View_Name.WAYPOINTS, "Waypoints")
        ])

        view_menu = self.window._menu_bar.addMenu("View")
        self._view_actions = {}
        for view_name, view_label in view_names.iteritems():
            action = QtGui.QAction(view_label, self.window)
            action.triggered.connect(partial(self.show_view, view_name))
            action.setCheckable(True)
            if view_name == self._current_view_name:
                action.setChecked(True)

            view_menu.addAction(action)
            self._view_actions[view_name] = action
