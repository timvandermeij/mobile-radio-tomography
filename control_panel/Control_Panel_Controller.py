from Control_Panel_View import Control_Panel_View_Name
from Control_Panel_Loading_View import Control_Panel_Loading_View
from Control_Panel_Reconstruction_View import Control_Panel_Reconstruction_View
from Control_Panel_Waypoints_View import Control_Panel_Waypoints_View
from ..core.USB_Manager import USB_Manager
from ..settings import Arguments

class Control_Panel_Controller(object):
    def __init__(self, central_widget, window):
        """
        Initialize the control panel controller.
        """

        # Set the central widget and window for loading views.
        self.central_widget = central_widget
        self.window = window

        # Create arguments (for obtaining various settings in views)
        # and a USB manager (for checking insertion of XBee devices).
        self.arguments = Arguments("settings.json", [])
        self.usb_manager = USB_Manager()

        # Show the loading view (default).
        self.show_view(Control_Panel_View_Name.LOADING)

    def show_view(self, name):
        """
        Show a new view, identified by `name`, and clear the current view.
        """

        views = {
            Control_Panel_View_Name.LOADING: Control_Panel_Loading_View,
            Control_Panel_View_Name.RECONSTRUCTION: Control_Panel_Reconstruction_View,
            Control_Panel_View_Name.WAYPOINTS: Control_Panel_Waypoints_View
        }

        if name not in views:
            raise ValueError("Unknown view name specified.")

        view = views[name](self)
        view.clear(self.central_widget.layout())
        view.show()
