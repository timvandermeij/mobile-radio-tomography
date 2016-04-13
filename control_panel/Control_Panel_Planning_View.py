import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.lines import Line2D
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
        self._settings_toolbar = QToolBarFocus(self._controller.app, "Settings")
        self._settings_toolbar.setMovable(False)
        self._settings_toolbar.setStyleSheet("QToolBar {spacing: 8px;}")

        self._forms = {}
        for component in ("planning", "planning_algorithm", "planning_problem"):
            form = SettingsWidget(self._controller.arguments, component,
                                  toolbar=self._settings_toolbar)

            self._settings_toolbar.addWidget(form)
            self._forms[component] = form

        self._controller.window.addToolBar(self._settings_toolbar)

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

        actions_toolbar = self._controller.window.addToolBar("Planning")
        actions_toolbar.setMovable(False)
        actions_toolbar.setSizePolicy(QtGui.QSizePolicy.Minimum,
                                      QtGui.QSizePolicy.Preferred)
        actions_toolbar.setStyleSheet("QToolBar {spacing: 8px;}")
        actions_toolbar.addAction(self._start_action)
        actions_toolbar.addAction(self._stop_action)

        self._plot_width, self._plot_height = self._settings.get("planning_plot_dimensions")

        # Create a progress bar.
        self._progress = QtGui.QProgressBar()
        self._progress.setMaximumWidth(self._plot_width)

        # Create the figure canvas for the main Pareto front image.
        self._front_axes, self._front_canvas = self._create_plot()

        # Register a picker to select a specific point in the Pareto front, 
        # which can then select one of the individuals.
        self._front_canvas.mpl_connect('pick_event', self._front_pick_event)

        self._item_width = self._plot_width / 4
        self._item_height = self._plot_height / 4

        self._listWidget = QtGui.QListWidget()
        frameWidth = self._listWidget.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        barWidth = self._listWidget.verticalScrollBar().sizeHint().width()
        self._listWidget.setFixedWidth(self._item_width + frameWidth + barWidth)
        self._listWidget.setCurrentRow(0)

        self._stackedLayout = QtGui.QStackedLayout()
        self._listWidget.currentRowChanged.connect(self._stackedLayout.setCurrentIndex)
        self._stackedLayout.currentChanged.connect(lambda i: self._redraw(i))

        # Create the layout and add the widgets.
        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addWidget(self._progress)
        vbox.addLayout(self._stackedLayout)
        vbox.addStretch(1)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addWidget(self._listWidget)
        hbox.addStretch(1)
        hbox.addLayout(vbox)
        hbox.addStretch(1)

        self._front_label = self._add_list_item("Pareto front",
                                                self._front_canvas)

    def _create_plot(self):
        dpi = plt.rcParams['figure.dpi']
        figsize = (self._plot_width / dpi, self._plot_height / dpi)

        figure = plt.figure(frameon=False, figsize=figsize)
        axes = figure.add_subplot(111)

        canvas = FigureCanvas(figure)
        canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        canvas.setFixedSize(self._plot_width, self._plot_height)
        canvas.setStyleSheet("background: transparent")

        return axes, canvas

    def _add_list_item(self, placeholder, canvas):
        list_item = QtGui.QListWidgetItem(placeholder)
        font = QtGui.QFont()
        font.setBold(True)
        height = QtGui.QFontInfo(font).pixelSize()
        list_item.setFont(font)
        list_item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        list_item.setSizeHint(QtCore.QSize(self._item_width, self._item_height + height))

        item_label = QtGui.QLabel()
        item_label.setFixedSize(self._item_width, self._item_height + height)
        item_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)

        self._listWidget.addItem(list_item)
        self._listWidget.setItemWidget(list_item, item_label)

        self._stackedLayout.addWidget(canvas)
        self._controller.app.processEvents()

        return item_label

    def _draw_list_item(self, label, canvas):
        pixmap = QtGui.QPixmap.grabWidget(canvas)
        image = pixmap.toImage()

        label_size = label.minimumSize()
        scaled_image = image.scaled(self._item_width, self._item_height)
        label.setPixmap(QtGui.QPixmap(scaled_image))

        self._controller.app.processEvents()

    def _draw_individual_solution(self, i, indices):
        axes = self._individual_axes[i]

        self._runner.get_positions_plot(i, indices.index(i), len(indices),
                                        axes=axes)

        self._individual_canvases[i].draw()
        self._draw_list_item(self._individual_labels[i],
                             self._individual_canvases[i])

    def _redraw(self, i):
        if i == 0:
            # The Pareto front is always redrawn when possible.
            return

        # The solution plots are indexed from 1 in the list widget, but from 
        # 0 in the algorithm population and plot object lists.
        i = i - 1

        indices = self._runner.get_indices()
        if i not in indices:
            # Solution is not feasible or there are no results yet.
            return

        self._draw_individual_solution(i, indices)

    def _front_pick_event(self, event):
        # We only want points on front lines.
        if not isinstance(event.artist, Line2D):
            return
        if len(event.ind) == 0:
            return True

        xdata = event.artist.get_xdata()
        ydata = event.artist.get_ydata()
        indices = event.ind

        for picked_point in zip(xdata[indices], ydata[indices]):
            points = self._runner.find_objectives(picked_point)
            if points:
                self._listWidget.setCurrentRow(points[0])
                return

    def _start(self):
        for component, form in self._forms.iteritems():
            settings = self._controller.arguments.get_settings(component)
            for key, value in form.get_values().iteritems():
                try:
                    settings.set(key, value)
                except ValueError:
                    return

        self._settings_toolbar.layout().setExpanded(False)
        self._start_action.setEnabled(False)
        self._stop_action.setEnabled(True)

        self._runner.activate()

        self._progress.setValue(0)
        self._progress.setRange(0, self._runner.get_iteration_limit())

        # Remove old individual items from the list widget, then add the new 
        # individuals in the population.
        for i in range(self._listWidget.count() - 1, 0, -1):
            self._listWidget.takeItem(i)
            self._stackedLayout.takeAt(i)
            plt.close(self._individual_canvases[i-1].figure)

        self._individual_labels = []
        self._individual_axes = []
        self._individual_canvases = []

        size = self._runner.get_population_size()
        plt.rcParams.update({'figure.max_open_warning': size + 1})

        for i in range(1, size + 1):
            axes, canvas = self._create_plot()

            label = self._add_list_item("Solution #{}".format(i), canvas)
            label.setStyleSheet("border-top: 1px solid grey")

            self._individual_labels.append(label)

            self._individual_axes.append(axes)
            self._individual_canvases.append(canvas)

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
            currentIndex = self._stackedLayout.currentIndex()

            self._runner.make_pareto_plot(self._front_axes)
            self._front_canvas.draw()
            self._draw_list_item(self._front_label, self._front_canvas)

            size = self._runner.get_population_size()
            indices = self._runner.get_indices()
            c = 0
            for i in range(size):
                if not self._runner.is_feasible(i):
                    self._individual_labels[i].setText("(infeasible)")
                elif currentIndex == i + 1 or self._runner.done:
                    self._draw_individual_solution(i, indices)
                else:
                    text = ", ".join([str(x) for x in self._runner.get_objectives(i)])
                    self._individual_labels[i].setText(text)

        self._updated = False

    def iteration_callback(self, algorithm, data):
        self._updated = True
