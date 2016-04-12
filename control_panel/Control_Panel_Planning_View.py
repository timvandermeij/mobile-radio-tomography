import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View
from Control_Panel_Widgets import QLineEditValidated
from ..planning.Runner import Planning_Runner

class Control_Panel_Planning_View(Control_Panel_View):
    def show(self):
        self._add_menu_bar()

        self._runner = Planning_Runner(self._controller.arguments,
                                       self._controller.thread_manager,
                                       self.iteration_callback)

        self._update_interval = self._settings.get("planning_update_interval")

        # Create the toolbar.
        toolbar = self._controller.window.addToolBar("Planning")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar {spacing: 8px;}")

        iteration_label = QtGui.QLabel("Number of iterations:")
        iteration_validator = QtGui.QIntValidator()
        iteration_validator.setBottom(1)
        iteration_box = QLineEditValidated()
        iteration_box.setText(str(self._runner.get_iteration_limit()))
        iteration_box.setValidator(iteration_validator)
        iteration_box.textEdited.connect(
            lambda: self._update_start_state(iteration_box)
        )

        stretch = QtGui.QWidget()
        stretch.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)

        self._start_action = QtGui.QAction(QtGui.QIcon("assets/start.png"),
                                           "Start",
                                           self._controller.central_widget)
        self._start_action.triggered.connect(
            lambda: self._start(int(iteration_box.text()))
        )

        self._stop_action = QtGui.QAction(QtGui.QIcon("assets/stop.png"),
                                           "Start",
                                           self._controller.central_widget)
        self._stop_action.setEnabled(False)
        self._stop_action.triggered.connect(
            lambda: self._stop()
        )

        toolbar.addWidget(iteration_label)
        toolbar.addWidget(iteration_box)
        toolbar.addWidget(stretch)
        toolbar.addAction(self._start_action)
        toolbar.addAction(self._stop_action)

        self._controller.window._toolbar = toolbar    

        # Create the figure canvas for the main Pareto front image.
        front_width, front_height = self._settings.get("planning_front_dimensions")

        self._front_figure = plt.figure(frameon=False,
                                        figsize=(front_width, front_height))
        self._front_axes = self._front_figure.add_axes([0, 0, 1, 1])
        self._front_canvas = FigureCanvas(self._front_figure)

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addStretch(1)
        hbox.addWidget(self._front_canvas)
        hbox.addStretch(1)

    def _update_start_state(self, iteration_box):
        self._start_action.setEnabled(iteration_box.hasAcceptableInput())

    def _start(self, t_max):
        self._start_action.setEnabled(False)
        self._stop_action.setEnabled(True)

        self._controller.app.processEvents()

        self._runner.set_iteration_limit(t_max)
        self._runner.activate()

        self._timer = QtCore.QTimer()
        self._timer.setInterval(self._update_interval * 1000)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._check)
        self._timer.start()

    def _stop(self):
        self._runner.deactivate()
        self._timer.stop()

        self._start_action.setEnabled(True)
        self._stop_action.setEnabled(False)

    def _check(self):
        if self._runner.done:
            self._stop()
            self._runner.make_pareto_plot(self._front_axes)
            self._front_canvas.draw()

    def iteration_callback(self, algorithm, data):
        self._current_data = data
        self._updated = True
