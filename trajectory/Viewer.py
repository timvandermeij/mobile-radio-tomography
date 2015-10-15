import math
import numpy as np

import pyglet
from pyglet.window import key
from pyglet.gl import *

from MockVehicle import MockVehicle

# Based on ideas from https://pyglet.googlecode.com/hg/examples/opengl.py and 
# https://greendalecs.wordpress.com/2012/04/21/3d-programming-in-python-part-1/
class Viewer(object):
    """
    3D environment scene viewer
    """

    def __init__(self, environment):
        self.environment = environment

    def start(self):
        self._setup()

        self.win = pyglet.window.Window(resizable=True)
        self.win.push_handlers(self)
        # Log all possible events
        self.win.push_handlers(pyglet.window.event.WindowEventLogger())

        pyglet.app.run()

    def _setup(self):
        # One-time GL setup
        glClearColor(1, 1, 1, 1)
        glColor3f(1, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_POINT_SPRITE)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glPointSize(50.0)

        self._reset_location()
        self._reset_movement()

        # Colors
        self.colors = []
        for i in range(len(self.environment.get_objects())):
            self.colors.append(np.random.rand(3))

    def _reset_location(self):
        # Rotation
        self.rx = 0.0
        self.ry = 0.0
        self.rz = 0.0

        # Translation
        self.tx = 0.0
        self.ty = 0.0
        self.tz = 0.0

    def _reset_movement(self):
        # Orientation (rotation change)
        self.ox = 0.0
        self.oy = 0.0
        self.oz = 0.0

        # Movement (translation change)
        self.mx = 0.0
        self.my = 0.0
        self.mz = 0.0

    def update(self, dt):
        self.tx = self.tx + self.mx
        self.ty = self.ty + self.my
        self.tz = self.tz + self.mz
        self.rx = (self.rx + dt * self.ox) % 360
        self.ry = (self.ry + dt * self.oy) % 360
        self.rz = (self.rz + dt * self.oz) % 360

        print("[{}, {}, {}]".format(self.tx, self.ty, self.tz))

    def _draw_polygon(self, face, i=-1, j=-1):
        glBegin(GL_POLYGON)
        for p in face:
            # We convert to GL standards here, where the second axis is the 
            # vertical axis. (lat,lon,alt) = (z,x,y) according to GL and we 
            # need to pass this function (x,y,z) coordinates, so cope with it.
            # All other variables in this function then make sense in this 
            # coordinate system.
            glVertex3f(p.lon, p.alt, p.lat)
        glEnd()

    def on_draw(self):
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw outlines only
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glLoadIdentity()
        glRotatef(self.rz, 0, 0, 1)
        glRotatef(self.ry, 0, 1, 0)
        glRotatef(self.rx, 1, 0, 0)
        glTranslatef(-self.tx, -self.ty, self.tz)

        i = 0
        for obj in self.environment.get_objects():
            glColor3f(*self.colors[i])
            if isinstance(obj, list):
                j = 0
                for face in obj:
                    self._draw_polygon(face, i, j)
                    j = j + 1
            elif isinstance(obj, tuple):
                self._draw_polygon(obj, i)

            i = i + 1

    def on_resize(self, width, height):
        # Override the default on_resize handler to create a 3D projection
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60., width / float(height), .1, 1000.)
        glMatrixMode(GL_MODELVIEW)
        return pyglet.event.EVENT_HANDLED

class Viewer_Interactive(Viewer):
    def __init__(self, environment):
        super(Viewer_Interactive, self).__init__(environment)
        self.vehicle = self.environment.get_vehicle()
        if isinstance(self.vehicle, MockVehicle):
            self.is_mock = True
        else:
            self.is_mock = False

        self.sensors = self.environment.get_distance_sensors()

    def _draw_polygon(self, face, i=-1, j=-1):
        if i != -1 and j != -1:
            for sensor in self.sensors:
                edge = sensor.get_current_edge()
                if isinstance(edge, list) and edge[0] == i and edge[1] == j:
                    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                    break

        super(Viewer_Interactive, self)._draw_polygon(face, i, j)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    def on_draw(self):
        super(Viewer_Interactive, self).on_draw()
        glBegin(GL_POINTS)
        glColor3f(1, 0, 0)
        for sensor in self.sensors:
            edge = sensor.get_current_edge()
            point = None
            if isinstance(edge, list):
                point = edge[-1]
            elif not isinstance(edge, tuple):
                point = edge

            if point is not None:
                glVertex3f(point.lon, point.alt, point.lat)

        glEnd()

    def update(self, dt):
        super(Viewer_Interactive, self).update(dt)
        if self.is_mock:
            self.vehicle.set_location(self.mz, self.mx, self.my)
            self.vehicle.attitude.yaw = self.ry * math.pi/180

        i = 0
        for sensor in self.sensors:
            angle = sensor.get_angle()
            sensor_distance = sensor.get_distance()
            print("Sensor {} distance: {} m (angle {})".format(i, sensor_distance, angle))
            i = i + 1

    def on_key_press(self, symbol, modifiers):
        if symbol == key.LEFT: # lon
            self.mx = -1.0
        elif symbol == key.RIGHT: # lon
            self.mx = 1.0
        elif symbol == key.DOWN: # alt
            self.my = -1.0
        elif symbol == key.UP: # alt
            self.my = 1.0
        elif symbol == key.MINUS or symbol == key.NUM_SUBTRACT: # lat (out)
            self.mz = -1.0
        elif symbol == key.PLUS or symbol == key.NUM_ADD: # lat (into)
            self.mz = 1.0
        elif symbol == key.R:
            self._reset_location()
        elif symbol == key.Q:
            pyglet.app.exit()
        else:
            return

        pyglet.clock.schedule(self.update)

    def on_key_release(self, symbol, modifiers):
        self._reset_movement()
        pyglet.clock.unschedule(self.update)

    def on_mouse_scroll(self, x, y, dx, dy):
        # Move into/outward
        self.mz = dy
        self.update(1.0)
        self.mz = 0.0

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.ry = self.ry + 360 * (dx / float(self.win.width))
        self.rx = self.rx - 360 * (dy / float(self.win.height))

class Viewer_Vehicle(Viewer):
    def __init__(self, environment, monitor):
        super(Viewer_Vehicle, self).__init__(environment)
        self.initial_location = self.environment.get_location()
        self.monitor = monitor
        pyglet.clock.schedule_interval(self.update, self.monitor.get_delay())

    def update(self, dt):
        if not self.monitor.step():
            pyglet.app.exit()

        location = self.environment.get_location()
        self.tx = location.lon - self.initial_location.lon
        self.ty = location.alt
        self.tz = location.lat - self.initial_location.lat

        self.ry = self.environment.get_yaw() * 180/math.pi
