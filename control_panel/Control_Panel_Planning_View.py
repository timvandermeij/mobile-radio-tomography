# Core imports
import re
from functools import partial

# Qt imports
from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

# matplotlib imports
import matplotlib
try:
    matplotlib.use("Qt4Agg")
except ValueError as e:
    raise ImportError("Could not load matplotlib backend: {}".format(e.message))
finally:
    import matplotlib.pyplot as plt

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.lines import Line2D

# Package imports
from Control_Panel_Reconstruction_Widgets import Grid
from Control_Panel_Settings_Widgets import SettingsTableWidget
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name
from ..planning.Runner import Planning_Runner
from ..waypoint.Waypoint import Waypoint_Type

class Planning_Sort_Order(object):
    NONE = -2
    FEASIBLE = -1

class Control_Panel_Planning_View(Control_Panel_View):
    def __init__(self, controller, settings):
        super(Control_Panel_Planning_View, self).__init__(controller, settings)

        # Set up the planning runner and related state and update variables.
        self._running = False
        self._runner = Planning_Runner(self._controller.arguments,
                                       self._controller.thread_manager,
                                       self._controller.import_manager,
                                       self.iteration_callback)

        self._updated = False
        self._update_interval = self._settings.get("planning_update_interval")

        # The fixed plot dimensions upon which we base our layout sizes as well 
        # as the plot canvases themselves. This avoids laggy resize events.
        self._plot_width, self._plot_height = self._settings.get("planning_plot_dimensions")

        # The size of miniature plot images in the list widget.
        self._item_width = self._plot_width / 3
        self._item_height = self._plot_height / 3

        # The number of items at the start of the list widget that are not 
        # individual solution plots; namely, the Pareto front and statistics 
        # graph. This is used for index conversion between the list widget and 
        # the planning population.
        self._overview_items = 2

        self._progress = None
        self._selectButton = None
        self._grid_button = None

        self._listWidget = None
        self._stackedLayout = None
        self._sortSelector = None
        self._toggle_button = None
        self._tabWidget = None

        self._forms = {}
        self._settings_container = None

        self._update_timer = None
        self._grid_timer = None
        self._grid_next_vehicle = None

        self._graph_label = None

        self._init()

    def show(self):
        self._add_menu_bar()

        # Create the progress bar.
        self._progress = QtGui.QProgressBar()
        self._progress.setMaximumWidth(self._plot_width)

        # Create a select button for selecting an individual feasible solution.
        self._selectButton = QtGui.QPushButton("Select")
        self._selectButton.setToolTip("Select current solution to use waypoints from")
        self._selectButton.setEnabled(False)
        self._selectButton.clicked.connect(self._select)

        self._grid_button = QtGui.QPushButton(QtGui.QIcon("assets/start.png"), "Grid")
        self._grid_button.setEnabled(False)
        self._grid_button.clicked.connect(self._start_grid)
        self._update_grid_button_state(running=False)

        # Create a list widget for selecting between different plots, namely 
        # the Pareto front plot, a graph with statistics and result plots of 
        # individual solutions. The list widget contains labels, current values 
        # of objective functions and/or miniature plot images.
        self._listWidget = QtGui.QListWidget()

        # Create a stacked layout for switching between the plot widgets, and 
        # connect it to the list widget and instant redrawing of the plot.
        self._stackedLayout = QtGui.QStackedLayout()
        self._listWidget.currentRowChanged.connect(self._stackedLayout.setCurrentIndex)
        self._stackedLayout.currentChanged.connect(self._redraw)

        # Create the sort selector.
        self._sortSelector = QtGui.QComboBox()
        self._sortSelector.currentIndexChanged.connect(self._resort)

        # Create the toggle button (using the stopped state as default).
        self._toggle_button = QtGui.QPushButton(QtGui.QIcon("assets/start.png"), "Start")
        self._toggle_button.clicked.connect(self._toggle)

        # Create the form layout and add the sort selector and toggle button.
        formLayout = QtGui.QFormLayout()
        formLayout.addRow("Sort order:", self._sortSelector)
        formLayout.addRow(self._toggle_button)

        # Create the layout and add all the widgets and other layouts into it.
        self._tabWidget = QtGui.QTabWidget()

        leftBox = QtGui.QVBoxLayout()
        leftBox.addWidget(self._tabWidget)
        leftBox.addLayout(formLayout)

        topLayout = QtGui.QHBoxLayout()
        topLayout.addWidget(self._grid_button)
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

        # Initialize more state variables and setup plots for initial display.
        self._setup()
        self._fill_forms()

        # Fill the tab widget.
        self._tabWidget.addTab(self._settings_container, "Settings")
        self._tabWidget.addTab(self._listWidget, "Runner state")

    def clear(self, layout=None):
        if layout is self._controller.central_widget.layout():
            self._stop()
            self._cleanup()

        super(Control_Panel_Planning_View, self).clear(layout)

    def _init(self):
        # Set variables that are altered during running to default state.
        self._individual_labels = []
        self._individual_axes = []
        self._individual_canvases = []
        self._individual_grids = []
        self._individual_stacks = []

        self._graph = None
        self._graph_plots = {}
        self._graph_data = {}

        self._front_canvas = None
        self._front_axes = None
        self._front_label = None

    def _cleanup(self):
        cleaner = QtCore.QObjectCleanupHandler()

        self._update_grid_button_state(running=False)

        # Remove old individual items from the list widget, then add the new 
        # individuals in the population.
        for i in range(self._listWidget.count() - 1, -1, -1):
            self._listWidget.itemWidget(self._listWidget.item(i)).close()
            self._listWidget.takeItem(i)
            self._stackedLayout.takeAt(i).widget().close()
            if i >= self._overview_items:
                self._individual_axes[i - self._overview_items].cla()
                canvas = self._individual_canvases[i - self._overview_items]
                canvas.figure.clf()
                plt.close(canvas.figure)
                cleaner.add(canvas)

        for plot in self._graph_plots.itervalues():
            plot.clear()

        if self._front_canvas is not None:
            self._front_axes.cla()
            self._front_canvas.figure.clf()
            plt.close(self._front_canvas.figure)
            cleaner.add(self._front_canvas)
            self._front_canvas = None

        if self._grid_timer is not None:
            self._grid_timer.stop()
            self._grid_timer = None

        if self._update_timer is not None:
            self._update_timer.stop()
            self._update_timer = None

        cleaner.clear()

        self._init()

    def _setup(self):
        # Create the figure canvas for the main Pareto front image.
        self._front_axes, self._front_canvas = self._create_plot()

        # Register a picker to select a specific point in the Pareto front, 
        # which can then select one of the individuals.
        self._front_canvas.mpl_connect('pick_event', self._front_pick_event)

        self._front_label = self._add_list_item("Pareto front",
                                                self._front_canvas, draw=False)

        self._listWidget.setCurrentRow(0)

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

    def _fill_forms(self):
        # Create the settings table widgets.
        self._forms = {}

        components = (
            "planning", "planning_runner",
            "planning_algorithm", "planning_problem",
            "planning_assignment", "planning_collision_avoidance"
        )
        prefix = self._controller.arguments.get_settings("planning").name
        pattern = r'^{}: ([a-z])'.format(re.escape(prefix))

        self._settings_container = QtGui.QScrollArea()
        self._settings_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        settings_layout = QtGui.QVBoxLayout()
        width = self._listWidget.sizeHint().width()

        for component in components:
            form = SettingsTableWidget(self._controller.arguments, component,
                                       include_parent=False)

            title = form.get_title()
            short_title = re.sub(pattern, lambda m: m.group(1).upper(),
                                 form.get_settings().name)
            settings_group = QtGui.QGroupBox(short_title)
            settings_group.setToolTip(title)
            settings_group.setCheckable(True)
            settings_group.toggled.connect(partial(self._toggle_settings, settings_group, form))
            settings_group.setStyleSheet("""
                QGroupBox::indicator { width: 0; height: 0 }
                QGroupBox::title {
                    padding: 0 3px;
                    border: 1px outset #aaaaaa;
                    background: #f0f0f0;
                }
            """)

            form.setFixedWidth(width)
            form_layout = QtGui.QHBoxLayout()
            form_layout.addWidget(form)
            form_layout.addStretch(1)

            settings_group.setLayout(form_layout)
            settings_layout.addWidget(settings_group)

            self._forms[component] = form

        settings_widget = QtGui.QWidget()
        settings_widget.setLayout(settings_layout)

        self._settings_container.setWidgetResizable(True)
        self._settings_container.setWidget(settings_widget)

    def _toggle_settings(self, settings_group, form, checked):
        form.setVisible(checked)
        settings_group.setFlat(not checked)

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

    def _create_grid(self):
        grid = Grid(size=self._plot_width)
        grid.setup(self._runner.problem.network_size)

        return grid

    def _add_list_item(self, placeholder, canvas, draw=True):
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
        if draw:
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

        # Enable or disable the buttons related to individuals. These are only 
        # active for feasible solutions at the end of the run.
        if item_index >= 0 and self._runner.done:
            if sort == Planning_Sort_Order.NONE:
                feasible = self._runner.is_feasible(item_index)
            else:
                feasible = item_index < len(indices)

            self._selectButton.setEnabled(feasible)
            self._grid_button.setEnabled(feasible)

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
        """
        Redraw a newly selected item index plot immediately.
        """

        if self._grid_timer is not None:
            self._grid_timer.stop()
            self._grid_timer = None
            self._update_grid_button_state(running=False)

        if item_index < self._overview_items:
            # The overview plots are always redrawn when possible, so we do not 
            # need to draw it here. Disable the buttons related to the 
            # individuals.
            self._selectButton.setEnabled(False)
            self._grid_button.setEnabled(False)
            return

        # The solution plots are indexed from 2 in the list widget, but from 
        # 0 in the algorithm population and plot object lists.
        item_index = item_index - self._overview_items

        self._individual_stacks[item_index].setCurrentIndex(0)

        indices = self._get_sort_indices()[1]
        if item_index >= len(indices):
            # Solution is not feasible or there are no results yet.
            return

        i = indices[item_index]
        self._draw_individual_solution(i, item_index, indices)

        # Enable or disable the buttons related to the individuals. These are 
        # only active for feasible solutions at the end of the run.
        if self._runner.done:
            feasible = self._runner.is_feasible(i)
            self._selectButton.setEnabled(feasible)
            self._grid_button.setEnabled(feasible)

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

        sort_indices = self._get_sort_indices()[1]
        for picked_point in zip(xdata[indices], ydata[indices]):
            points = self._runner.find_objectives(picked_point)
            for i in points:
                try:
                    item_index = sort_indices.index(i) + self._overview_items
                except ValueError:
                    continue

                self._listWidget.setCurrentRow(item_index)
                return

    def _toggle(self):
        """
        Handle the toggle button to toggle the state of the planning runner 
        (start or stop).
        """

        if not self._running:
            self._start()
        else:
            self._stop()

    def _update_running(self, running):
        """
        Toggle the running state of the toggle button (started of stopped).
        """

        if not running:
            self._toggle_button.setIcon(QtGui.QIcon("assets/start.png"))
            self._toggle_button.setText("Start")
        else:
            self._toggle_button.setIcon(QtGui.QIcon("assets/stop.png"))
            self._toggle_button.setText("Stop")

        self._running = running

    def _start(self):
        # Update the settings from the toolbox forms.
        for form in self._forms.itervalues():
            settings = form.get_settings()
            try:
                values, disallowed = form.get_all_values()
                form.check_disallowed(disallowed)
            except ValueError as e:
                QtGui.QMessageBox.critical(self._controller.central_widget,
                                           "Invalid value", e.message)
                return

            for key, value in values.iteritems():
                try:
                    settings.set(key, value)
                except ValueError as e:
                    QtGui.QMessageBox.critical(self._controller.central_widget,
                                               "Settings error", e.message)
                    return

        # Update the toggle button state
        self._update_running(True)

        # Set the running state for the planning runner, and stop the RF sensor from 
        # taking up cycles during the algorithm.
        self._controller.rf_sensor.deactivate()
        self._runner.activate()

        # Change the tab widget to show the runner state.
        self._tabWidget.setCurrentIndex(1)
        self._selectButton.setEnabled(False)
        self._grid_button.setEnabled(False)

        # Update the progress bar to show the correct iteration completion.
        t_max = self._runner.get_iteration_limit()

        self._progress.setValue(0)
        self._progress.setRange(0, t_max)

        # Clean up an old run and set up the new Pareto front plot and label.
        self._cleanup()
        self._setup()

        # Ensure we are allowed to make the matplotlib figures that we need, 
        # but do not allow more for memory leak detection.
        size = self._runner.get_population_size()
        plt.rcParams.update({'figure.max_open_warning': size + 1})

        # Create the statistics graph.
        self._graph = self._create_graph()
        self._graph_label = self._add_list_item("Statistics", self._graph)
        self._graph_label.setStyleSheet("border-top: 1px solid grey")

        # Create the plots and labels for the individual solutions.
        for i in range(1, size + 1):
            stack = QtGui.QStackedLayout()
            item_widget = QtGui.QWidget()
            item_widget.setLayout(stack)

            label = self._add_list_item("Solution #{}".format(i), item_widget)
            label.setStyleSheet("border-top: 1px solid grey")

            axes, canvas = self._create_plot()
            grid = self._create_grid()

            stack.addWidget(canvas)
            stack.addWidget(grid)

            self._individual_labels.append(label)

            self._individual_axes.append(axes)
            self._individual_canvases.append(canvas)

            self._individual_grids.append(grid)
            self._individual_stacks.append(stack)

        # Start the timer for updating plots and labels.
        self._update_timer = QtCore.QTimer()
        self._update_timer.setInterval(self._update_interval * 1000)
        self._update_timer.setSingleShot(False)
        self._update_timer.timeout.connect(self._check)
        self._update_timer.start()

    def _stop(self):
        # Set the planning runner state to stopped, and reactivate the RF sensor.
        self._update_running(False)
        self._runner.stop()
        self._controller.rf_sensor.activate()

    def _check(self):
        # Update progress bar completion percentage every time, not only when 
        # new iteration callback data has arrived.
        self._progress.setValue(self._runner.get_iteration_current())

        # Stop the runner and update timer if the planning is done, then check 
        # for updates and final data.
        if self._runner.done or not self._running:
            self._stop()
            self._update_timer.stop()

        if self._updated:
            # Update the graph with updated iteration statistics.
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
            # Draw the plots for the Pareto front and any selected solution.
            self._runner.make_pareto_plot(self._front_axes)
            self._front_canvas.draw()
            self._draw_list_item(self._front_label, self._front_canvas)

            self._draw_solutions()

        self._updated = False

    def _select(self):
        i = self._stackedLayout.currentIndex() - self._overview_items
        if i < 0 or not self._runner.is_feasible(i):
            return

        waypoints = self._runner.get_assignment(i, export=True)

        self._controller.set_view_data(Control_Panel_View_Name.WAYPOINTS,
                                       "waypoints", waypoints)
        self._controller.show_view(Control_Panel_View_Name.WAYPOINTS)

    def _start_grid(self):
        i = self._stackedLayout.currentIndex() - self._overview_items
        if i < 0 or not self._runner.is_feasible(i):
            return

        self._update_grid_button_state(running=self._grid_timer is None)
        self._individual_grids[i].clear()
        self._grid_next_vehicle = None

        if self._grid_timer is not None:
            self._grid_timer.stop()
            self._grid_timer = None
            self._individual_stacks[i].setCurrentIndex(0)
            return

        self._individual_stacks[i].setCurrentIndex(1)

        waypoints = self._runner.get_assignment(i, export=False)

        self._grid_timer = QtCore.QTimer()
        self._grid_timer.setInterval(self._update_interval * 1000)
        self._grid_timer.setSingleShot(False)
        self._grid_timer.timeout.connect(partial(self._update_grid, waypoints))
        self._grid_timer.start()

    def _update_grid_button_state(self, running=False):
        if running:
            self._grid_button.setIcon(QtGui.QIcon("assets/stop.png"))
            self._grid_button.setToolTip("Show full solution")
        else:
            self._grid_button.setIcon(QtGui.QIcon("assets/start.png"))
            self._grid_button.setToolTip("Show order of links")

    def _update_grid(self, waypoints):
        i = self._stackedLayout.currentIndex() - self._overview_items
        if i < 0:
            self._grid_timer.stop()
            self._grid_timer = None
            return

        if all(len(points) == 0 for points in waypoints.itervalues()):
            # Stop the timer but do not remove it. It is removed when the user 
            # switches the views again.
            self._grid_timer.stop()
            return

        if self._grid_next_vehicle is not None:
            vehicle = self._grid_next_vehicle
            points = waypoints[vehicle]
            self._grid_next_vehicle = None
        else:
            vehicle, points = max(waypoints.iteritems(),
                                  key=lambda pair: len(pair[1]))

        if len(points) == 0:
            # There may be other vehicles than this one that still have points, 
            # so try those next time.
            return

        # Determine the source coordinates from the waypoint.
        waypoint = points[0]
        geometry = self._runner.problem.geometry
        source = geometry.get_coordinates(waypoint.location)[:2]
        grid = self._individual_grids[i]

        if waypoint.name != Waypoint_Type.WAIT:
            # Show waypoints with other types like home or pass as a new sensor 
            # position, but ignore it otherwise.
            grid.add_sensor(vehicle, source)
            del points[0]
            return

        # Determine the other vehicle's ID, and attempt to find the 
        # corresponding waypoint.
        other_vehicle = waypoint.wait_id

        other_waypoint = waypoints[other_vehicle][0]
        if other_waypoint.name != Waypoint_Type.WAIT:
            # Ignore waypoints with other types like home or pass, but try this 
            # same pair again next time.
            del waypoints[other_vehicle][0]
            self._grid_next_vehicle = vehicle
            return

        if other_waypoint.wait_id != vehicle:
            # The other vehicle is waiting for yet another vehicle, so try to 
            # resolve this synchronization next time.
            self._grid_next_vehicle = other_vehicle
            return

        # Determine the target coordinates and show the link.
        target = geometry.get_coordinates(other_waypoint.location)[:2]
        grid.add_link(source, target)
        grid.add_sensor(vehicle, source)
        grid.add_sensor(other_vehicle, target)

        del points[0]
        del waypoints[other_vehicle][0]

    def _add_graph_data(self, name, value, iteration):
        if name not in self._graph_data:
            self._graph_data[name] = {"x": [], "y": []}

        self._graph_data[name]["x"].append(iteration)
        self._graph_data[name]["y"].append(value)

    def iteration_callback(self, algorithm, data):
        self._updated = True

        t = data["iteration"]
        speed = t / float(data["cur_time"])
        self._add_graph_data("it/second", speed, t)
        for key, value in data["deletions"].iteritems():
            self._add_graph_data(key, value, t)
