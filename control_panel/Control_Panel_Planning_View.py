import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.lines import Line2D
import matplotlib.pyplot as plt

import pyqtgraph as pg

from PyQt4 import QtCore, QtGui
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name
from Control_Panel_Widgets import QToolBarFocus
from Control_Panel_Settings_Widgets import SettingsWidget
from ..planning.Runner import Planning_Runner

class Planning_Sort_Order(object):
    NONE = -2
    FEASIBLE = -1

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
        components = ("planning", "planning_assignment", "planning_algorithm",
                      "planning_problem")
        for component in components:
            form = SettingsWidget(self._controller.arguments, component,
                                  toolbar=self._settings_toolbar)

            self._settings_toolbar.addWidget(form)
            self._forms[component] = form

        self._controller.window.addToolBar(self._settings_toolbar)

        # Create the actions toolbar
        self._start_action = QtGui.QAction(QtGui.QIcon("assets/start.png"),
                                           "Start",
                                           self._controller.central_widget)
        self._start_action.triggered.connect(self._start)

        self._stop_action = QtGui.QAction(QtGui.QIcon("assets/stop.png"),
                                           "Stop",
                                           self._controller.central_widget)
        self._stop_action.setEnabled(False)
        self._stop_action.triggered.connect(self._stop)

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

        self._selectButton = QtGui.QPushButton()
        self._selectButton.setText("Select")
        self._selectButton.setToolTip("Select current solution to use waypoints from")
        self._selectButton.setEnabled(False)
        self._selectButton.clicked.connect(self._select)

        # Create the figure canvas for the main Pareto front image.
        self._front_axes, self._front_canvas = self._create_plot()

        # Register a picker to select a specific point in the Pareto front, 
        # which can then select one of the individuals.
        self._front_canvas.mpl_connect('pick_event', self._front_pick_event)

        self._overview_items = 2

        self._item_width = self._plot_width / 4
        self._item_height = self._plot_height / 4

        self._listWidget = QtGui.QListWidget()

        self._stackedLayout = QtGui.QStackedLayout()
        self._listWidget.currentRowChanged.connect(self._stackedLayout.setCurrentIndex)
        self._stackedLayout.currentChanged.connect(lambda i: self._redraw(i))

        self._sortSelector = QtGui.QComboBox()
        self._sortSelector.currentIndexChanged.connect(lambda i: self._resort(i))

        self._reset()

        # Create the layout and add the widgets.
        formLayout = QtGui.QFormLayout()
        formLayout.addRow("Sort order:", self._sortSelector)

        leftBox = QtGui.QVBoxLayout()
        leftBox.addWidget(self._listWidget)
        leftBox.addLayout(formLayout)

        topLayout = QtGui.QHBoxLayout()
        topLayout.addWidget(self._progress)
        topLayout.addWidget(self._selectButton)

        rightBox = QtGui.QVBoxLayout()
        rightBox.addStretch(1)
        rightBox.addLayout(topLayout)
        rightBox.addLayout(self._stackedLayout)
        rightBox.addStretch(1)

        hbox = QtGui.QHBoxLayout(self._controller.central_widget)
        hbox.addLayout(leftBox)
        hbox.addStretch(1)
        hbox.addLayout(rightBox)
        hbox.addStretch(1)

        self._front_label = self._add_list_item("Pareto front",
                                                self._front_canvas)

    def _reset(self):
        self._listWidget.setCurrentRow(0)

        # Remove old individual items from the list widget, then add the new 
        # individuals in the population.
        for i in range(self._listWidget.count() - 1, 0, -1):
            self._listWidget.takeItem(i)
            self._stackedLayout.takeAt(i)
            if i >= self._overview_items:
                canvas = self._individual_canvases[i - self._overview_items]
                plt.close(canvas.figure)

        # Reset variables that are altered during running to default state.
        self._individual_labels = []
        self._individual_axes = []
        self._individual_canvases = []

        self._graph = None
        self._graph_plots = {}
        self._graph_data = {}
        self._graph_label = None

        # Populate the sort selector with current problem's objectives.
        self._populate_sort_selector()

    def _populate_sort_selector(self):
        # Keep the current index while repopulating.
        currentIndex = self._sortSelector.currentIndex()

        self._sortSelector.clear()

        self._sortSelector.addItem("Unsorted population")
        self._sortSelector.addItem("Feasibility")

        for f, name in enumerate(self._runner.problem.get_objective_names()):
            self._sortSelector.addItem("Objective {} ({})".format(f+1, name))

        self._sortSelector.setCurrentIndex(max(0, currentIndex))

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

    def _create_graph(self):
        # Enable antialiasing and use a transparent background with black 
        # text/lines.
        pg.setConfigOptions(antialias=True, background=None, foreground="k")

        graph = pg.PlotWidget()
        graph.setStyleSheet("background: transparent")
        graph.setXRange(0, self._runner.get_iteration_limit())
        graph.setLabel("left", "Count")
        graph.setLabel("bottom", "Iteration")
        graph.addLegend()

        return graph

    def _add_list_item(self, placeholder, canvas):
        list_item = QtGui.QListWidgetItem(placeholder)
        font = QtGui.QFont()
        font.setBold(True)
        height = QtGui.QFontInfo(font).pixelSize()
        list_item.setFont(font)
        list_item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        list_item.setSizeHint(QtCore.QSize(self._item_width, self._item_height + height))

        item_label = QtGui.QLabel()
        item_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)

        self._listWidget.addItem(list_item)
        self._listWidget.setItemWidget(list_item, item_label)

        self._stackedLayout.addWidget(canvas)
        self._controller.app.processEvents()

        return item_label

    def _draw_list_item(self, label, canvas):
        pixmap = QtGui.QPixmap.grabWidget(canvas)
        # Scale the plot to a miniature. We do not care about the aspect ratio 
        # since we force this through the plot and item sizes, but we want 
        # a smooth transformation.
        label.setPixmap(pixmap.scaled(self._item_width, self._item_height,
                                      QtCore.Qt.IgnoreAspectRatio,
                                      QtCore.Qt.SmoothTransformation))

        self._controller.app.processEvents()

    def _draw_individual_solution(self, i, item_index, indices):
        axes = self._individual_axes[item_index]

        # The ranking of the solution in the sorted list is given in 
        # item_index, while i is the actual index in the population.
        self._runner.get_positions_plot(i, item_index, len(indices), axes=axes)

        self._individual_canvases[item_index].draw()
        self._draw_list_item(self._individual_labels[item_index],
                             self._individual_canvases[item_index])

    def _get_sort_indices(self):
        # The sort order index, which is -2 for unsorted and -1 for sort 
        # feasible solutions first.
        sort = self._sortSelector.currentIndex() + Planning_Sort_Order.NONE
        indices = self._runner.get_indices(sort=sort)

        return sort, indices

    def _draw_solutions(self):
        # The selected index in the list widget and stacked layout.
        # The solution plots are indexed from 2 in the list widget, but from 
        # 0 in the algorithm population and plot object lists.
        currentIndex = self._stackedLayout.currentIndex()
        item_index = currentIndex - self._overview_items

        sort, indices = self._get_sort_indices()

        if item_index >= 0:
            if sort == Planning_Sort_Order.NONE:
                feasible = self._runner.is_feasible(item_index)
            else:
                feasible = item_index < len(indices)

            self._selectButton.setEnabled(feasible)

        size = self._runner.get_population_size()

        if sort == Planning_Sort_Order.NONE:
            sort_order = range(size)
        else:
            sort_order = list(indices)
            sort_order.extend(i for i in range(size) if i not in sort_order)

        # The `index` is the index in the list widget (after sorting), while 
        # `i` is the index inside the entire population.
        for index, i in enumerate(sort_order):
            if not self._runner.is_feasible(i):
                self._individual_labels[index].setText("(infeasible)")
            elif index == item_index or self._runner.done:
                self._draw_individual_solution(i, index, indices)
            else:
                text = ", ".join(str(x) for x in self._runner.get_objectives(i))
                self._individual_labels[index].setText(text)

    def _redraw(self, item_index):
        # Redraw a newly selected item index plot immediately.

        if item_index < self._overview_items:
            # The overview plots are always redrawn when possible, so we do not 
            # need to draw it here. Disable the select button.
            self._selectButton.setEnabled(False)
            return

        # The solution plots are indexed from 2 in the list widget, but from 
        # 0 in the algorithm population and plot object lists.
        item_index = item_index - self._overview_items

        sort, indices = self._get_sort_indices()
        if item_index >= len(indices):
            # Solution is not feasible or there are no results yet.
            return

        i = indices[item_index]
        self._draw_individual_solution(i, item_index, indices)

        if self._runner.done:
            self._selectButton.setEnabled(self._runner.is_feasible(i))

    def _resort(self, sort_index):
        if len(self._individual_labels) == 0:
            return

        # Clear labels and then start resorting.
        for label in self._individual_labels:
            label.clear()

        self._draw_solutions()

    def _front_pick_event(self, event):
        # We only want points on front lines.
        if not isinstance(event.artist, Line2D):
            return
        # Events with no picked point indices are not of interest.
        if len(event.ind) == 0:
            return
        # If we just changed to one solution, do not handle more fired events.
        if self._listWidget.currentRow() != 0:
            return

        xdata = event.artist.get_xdata()
        ydata = event.artist.get_ydata()
        indices = event.ind

        sort, sort_indices = self._get_sort_indices()
        for picked_point in zip(xdata[indices], ydata[indices]):
            points = self._runner.find_objectives(picked_point)
            for i in points:
                try:
                    item_index = sort_indices.index(i) + self._overview_items
                except ValueError:
                    continue

                self._listWidget.setCurrentRow(item_index)
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
        self._selectButton.setEnabled(False)

        self._runner.activate()

        t_max = self._runner.get_iteration_limit()

        self._progress.setValue(0)
        self._progress.setRange(0, t_max)

        self._reset()

        size = self._runner.get_population_size()
        plt.rcParams.update({'figure.max_open_warning': size + 1})

        self._graph = self._create_graph()
        self._graph_label = self._add_list_item("Statistics", self._graph)
        self._graph_label.setStyleSheet("border-top: 1px solid grey")

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

        if self._updated:
            c = 0
            for name, data in self._graph_data.iteritems():
                if name not in self._graph_plots:
                    color = pg.intColor(c, hues=len(self._graph_data),
                                        maxValue=200)
                    plot = self._graph.plot(symbol='o', symbolBrush=color,
                                            symbolSize=5, pen=color, name=name)
                    self._graph_plots[name] = plot

                self._graph_plots[name].setData(data)
                c += 1

            self._draw_list_item(self._graph_label, self._graph)

        if self._runner.done or self._updated:
            self._runner.make_pareto_plot(self._front_axes)
            self._front_canvas.draw()
            self._draw_list_item(self._front_label, self._front_canvas)

            self._draw_solutions()

        self._updated = False

    def _select(self):
        currentIndex = self._stackedLayout.currentIndex()
        if currentIndex == 0:
            return

        i = currentIndex - self._overview_items
        if not self._runner.is_feasible(i):
            return

        positions, unsnappable = self._runner.get_positions(i)

        self._controller.set_view_data(Control_Panel_View_Name.WAYPOINTS,
                                       "waypoints", positions.tolist())
        self._controller.show_view(Control_Panel_View_Name.WAYPOINTS)

    def _add_graph_data(self, name, value, iteration):
        if name not in self._graph_data:
            self._graph_data[name] = {"x": [], "y": []}

        self._graph_data[name]["x"].append(iteration)
        self._graph_data[name]["y"].append(value)

    def iteration_callback(self, algorithm, data):
        self._updated = True

        t = data["iteration"]
        speed = t / float(data["cur_time"])
        self._add_graph_data("it/second",  speed, t)
        for key, value in data["deletions"].iteritems():
            self._add_graph_data(key, value, t)
