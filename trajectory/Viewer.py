import math
import numpy as np

import pyglet
from pyglet.window import key
from pyglet.gl import *

from MockVehicle import MockVehicle, MockAttitude

# Based on ideas from https://pyglet.googlecode.com/hg/examples/opengl.py and 
# https://greendalecs.wordpress.com/2012/04/21/3d-programming-in-python-part-1/
class Viewer(object):
    """
    3D environment scene viewer
    """

    def __init__(self, environment, settings=None):
        self.environment = environment

        if settings is None:
            arguments = self.environment.get_arguments()
            settings = arguments.get_settings("environment_viewer")

        self.settings = settings

        self.geometry = self.environment.get_geometry()
        self.initial_location = self.environment.get_location()

    def start(self):
        self._setup()

        self.win = pyglet.window.Window(resizable=True)
        self.win.push_handlers(self)

        pyglet.app.run()

    def _setup(self):
        # One-time GL setup
        glClearColor(1, 1, 1, 1)
        glColor3f(1, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)

        self._reset_location()
        self._reset_movement()

        self._load_objects()

    def _load_objects(self):
        self.points = []
        self.colors = []
        self.objects = []
        for obj in self.environment.get_objects():
            self.colors.append(np.random.rand(3))
            if isinstance(obj, list):
                faces = []
                for face in obj:
                    faces.append(self._load_polygon(face))

                self.objects.append(faces)
            elif isinstance(obj, tuple):
                points = self._load_polygon(obj)
                lower = lambda p: (p[0], 0.0, p[2])
                faces = []
                for edge in self.geometry.get_point_edges(points):
                    poly = (edge[0], edge[1], lower(edge[1]), lower(edge[0]))
                    faces.append(poly)

                self.objects.append(faces)

    def _load_polygon(self, points):
        return tuple(self._convert_point(p) for p in points)

    def _convert_point(self, p):
        # Convert coordinates to meters
        dlat, dlon, dalt = self.geometry.diff_location_meters(self.initial_location, p)
        # We convert to GL standards here, where the second axis is the 
        # vertical axis. (lat,lon,alt) = (z,x,y) according to GL and we need to 
        # pass this function (x,y,z) coordinates, so cope with it.
        # Also, the z axis comes "out of the screen" (but only when drawing, 
        # not when using screen transforms) rather than having the latitude 
        # increase northward, so we have to flip the entire perspective for the 
        # z value.
        # See http://stackoverflow.com/a/12336360 for an overview.
        return [dlon, dalt, -dlat]

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
        location = self.environment.get_location(dt * self.mz, dt * self.mx, dt * self.my)
        self.tz, self.tx, self.ty = self.geometry.diff_location_meters(self.initial_location, location)

        self.rx = (self.rx + dt * self.ox) % 360
        self.ry = (self.ry + dt * self.oy) % 360
        self.rz = (self.rz + dt * self.oz) % 360

        return location

    def _rotate(self, east, up, south, rotX, rotY, rotZ):
        # Rotations for each axis in radians
        x = rotX * math.pi/180
        y = rotY * math.pi/180
        z = rotZ * math.pi/180
        rX = [east, up * math.cos(x) - south * math.sin(x), up * math.sin(x) + south * math.cos(x)]
        rY = [rX[0] * math.cos(y) + rX[2] * math.sin(y), rX[1], rX[2] * math.cos(y) - rX[0] * math.sin(y)]
        rZ = [rY[0] * math.cos(z) - rY[1] * math.sin(z), rY[0] * math.sin(z) + rY[1] * math.cos(z), rY[2]]
        return rZ

    def move(self, east, up, south):
        dx, dy, dz = self._rotate(east, up, south, self.rx, self.ry, self.rz)
        self.mx = dx
        self.my = dy
        self.mz = dz

    def _draw_polygon(self, face, i=-1, j=-1):
        glBegin(GL_POLYGON)
        for p in face:
            glVertex3f(*p)
        glEnd()

    def add_point(self, point):
        self.points.append(self._convert_point(point))

    def on_expose(self):
        pass

    def on_draw(self):
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw outlines only
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glLoadIdentity()
        glRotatef(self.rx, 1, 0, 0)
        glRotatef(self.ry, 0, 1, 0)
        glRotatef(self.rz, 0, 0, 1)
        glTranslatef(-self.tx, -self.ty, self.tz)

        i = 0
        for obj in self.objects:
            glColor3f(*self.colors[i])
            if isinstance(obj, list):
                j = 0
                for face in obj:
                    self._draw_polygon(face, i, j)
                    j = j + 1
            elif isinstance(obj, tuple):
                self._draw_polygon(obj, i)

            i = i + 1

        glBegin(GL_POINTS)
        glColor3f(1, 0, 0)
        for point in self.points:
            glVertex3f(*point)
        glEnd()

    def on_resize(self, width, height):
        # Override the default on_resize handler to create a 3D projection
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60., width / float(height), .1, 1000.)
        glMatrixMode(GL_MODELVIEW)
        # Force a redraw
        self.win.invalid = True
        return pyglet.event.EVENT_HANDLED

class Viewer_Interactive(Viewer):
    def __init__(self, environment, settings):
        super(Viewer_Interactive, self).__init__(environment, settings)
        self.vehicle = self.environment.get_vehicle()
        if isinstance(self.vehicle, MockVehicle):
            self.is_mock = True
        else:
            self.is_mock = False

        self.sensors = self.environment.get_distance_sensors()
        self.camera_speed = self.settings.get("camera_speed") # meters/second
        self.rotate_speed = self.settings.get("rotate_speed") # degrees/second

    def _draw_polygon(self, face, i=-1, j=-1):
        if i != -1 and j != -1:
            for sensor in self.sensors:
                edge = sensor.get_current_edge()
                if isinstance(edge, list) and edge[0] == i and edge[1] == j:
                    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                    break

        super(Viewer_Interactive, self)._draw_polygon(face, i, j)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    def update(self, dt):
        location = super(Viewer_Interactive, self).update(dt)
        if self.is_mock:
            self.vehicle.location = location
            self.vehicle.attitude = MockAttitude(self.rx * math.pi/180, self.ry * math.pi/180, 0.0)

        self.points = []
        i = 0
        for sensor in self.sensors:
            angle = sensor.get_angle()
            sensor_distance = sensor.get_distance()
            loc = self.geometry.get_location_angle(location, sensor_distance, angle)
            self.add_point(loc)
            print("Sensor {} distance: {} m (angle {})".format(i, sensor_distance, angle))
            i = i + 1

    def on_key_press(self, symbol, modifiers):
        if symbol == key.LEFT or symbol == key.A: # lon, west
            self.move(-self.camera_speed, 0.0, 0.0)
        elif symbol == key.RIGHT or symbol == key.D: # lon, east
            self.move(self.camera_speed, 0.0, 0.0)
        elif symbol == key.DOWN: # alt, down
            self.move(0.0, -self.camera_speed, 0.0)
        elif symbol == key.UP: # alt, up
            self.move(0.0, self.camera_speed, 0.0)
        elif symbol == key.NUM_SUBTRACT or symbol == key.S: # lat, north
            self.move(0.0, 0.0, -self.camera_speed)
        elif symbol == key.NUM_ADD or symbol == key.W: # lat, south
            self.move(0.0, 0.0, self.camera_speed)
        elif symbol == key.I:
            self.ox = -self.rotate_speed
        elif symbol == key.K:
            self.ox = self.rotate_speed
        elif symbol == key.J:
            self.oy = -self.rotate_speed
        elif symbol == key.L:
            self.oy = self.rotate_speed
        elif symbol == key.R:
            self._reset_location()
        elif symbol == key.Q:
            pyglet.app.exit()
            return
        else:
            return

        pyglet.clock.schedule(self.update)
        # Ensure update function is called immediately and not have a large 
        # time delta caused by delay for the first update.
        pyglet.clock.get_default().update_time()
        pyglet.clock.tick()

    def on_key_release(self, symbol, modifiers):
        self._reset_movement()
        pyglet.clock.unschedule(self.update)

    def on_mouse_scroll(self, x, y, dx, dy):
        # Move into/outward
        self.move(0.0, 0.0, dy)
        self.update(1.0)
        self._reset_movement()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.rx = self.rx - (self.rotate_speed / self.win.width) * dy
        self.ry = self.ry + (self.rotate_speed / self.win.height) * dx

    def on_mouse_release(self, x, y, buttons, modifiers):
        self.update(0.0)

class Viewer_Vehicle(Viewer):
    def __init__(self, environment, monitor):
        super(Viewer_Vehicle, self).__init__(environment)
        self.monitor = monitor
        pyglet.clock.schedule_interval(self.update, self.monitor.get_delay())

    def update(self, dt):
        if not self.monitor.step(self.add_point):
            pyglet.app.exit()

        super(Viewer_Vehicle, self).update(0.0)
        self.ry = self.environment.get_yaw() * 180/math.pi
