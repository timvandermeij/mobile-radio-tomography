import math
import numpy as np

import pyglet
from pyglet.window import key
from pyglet.gl import *

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

        self.win = pyglet.window.Window()
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

        print("[{}, {}, {}]".format(-self.tx, -self.ty, self.tz))

    def _draw_polygon(self, face):
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
                for face in obj:
                    self._draw_polygon(face)
            elif isinstance(obj, tuple):
                self._draw_polygon(obj)

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
