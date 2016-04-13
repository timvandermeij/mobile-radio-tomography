import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View
from Control_Panel_Widgets import SettingsWidget, QToolBarFocus
from ..planning.Runner import Planning_Runner

class Control_Panel_Planning_View(Control_Panel_View):
    def show(self):
        self._add_menu_bar()

        self._runner = Planning_Runner(self._controller.arguments,
                                       self._controller.thread_manager,
                                       self.iteration_callback)

        self._updated = False
        self._update_interval = self._settings.get("planning_update_interval")

        # Create the settings toolbar.
        toolbar = QToolBarFocus(self._controller.app, "Settings")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar {spacing: 8px;}")

        self._forms = {}
        for component in ("planning", "planning_algorithm", "planning_problem"):
            self._forms[component] = SettingsWidget(self._controller.arguments,
                                                    component, toolbar)
            toolbar.addWidget(self._forms[component])

        self._controller.window.addToolBar(toolbar)

        # Create the actions toolbar
        self._start_action = QtGui.QAction(QtGui.QIcon("assets/start.png"),
                                           "Start",
                                           self._controller.central_widget)
        self._start_action.triggered.connect(lambda: self._start())

        self._stop_action = QtGui.QAction(QtGui.QIcon("assets/stop.png"),
                                           "Stop",
                                           self._controller.central_widget)
        self._stop_action.setEnabled(False)
        self._stop_action.triggered.connect(lambda: self._stop())

        actions = self._controller.window.addToolBar("Planning")
        actions.setMovable(False)
        actions.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        actions.setStyleSheet("QToolBar {spacing: 8px;}")
        actions.addAction(self._start_action)
        actions.addAction(self._stop_action)

        # Create a progress bar.
        self._progress = QtGui.QProgressBar()
        self._progress.setValue(0)
        self._progress.reset()

        # Create the figure canvas for the main Pareto front image.
        front_width, front_height = self._settings.get("planning_front_dimensions")

        self._front_figure = plt.figure(frameon=False,
                                        figsize=(front_width, front_height))
        self._front_axes = self._front_figure.add_subplot(111)
        self._front_canvas = FigureCanvas(self._front_figure)

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addWidget(self._progress)
        vbox.addStretch(1)
        vbox.addWidget(self._front_canvas)
        vbox.addStretch(1)

    def _start(self):
        for component, form in self._forms.iteritems():
            settings = self._controller.arguments.get_settings(component)
            for key, value in form.get_values().iteritems():
                try:
                    settings.set(key, value)
                except ValueError:
                    return

        self._start_action.setEnabled(False)
        self._stop_action.setEnabled(True)

        self._runner.activate()

        self._progress.setValue(0)
        self._progress.setRange(0, self._runner.get_iteration_limit())

        self._timer = QtCore.QTimer()
        self._timer.setInterval(self._update_interval * 1000)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._check)
        self._timer.start()

    def _stop(self):
        self._runner.deactivate()

        self._start_action.setEnabled(True)
        self._stop_action.setEnabled(False)

    def _check(self):
        self._progress.setValue(self._runner.get_iteration_current())
        if self._runner.done:
            self._stop()
            self._timer.stop()

        if self._runner.done or self._updated:
            self._runner.make_pareto_plot(self._front_axes)
            self._front_canvas.draw()

        self._updated = False

    def iteration_callback(self, algorithm, data):
        self._updated = True
