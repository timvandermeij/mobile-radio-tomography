from collections import deque
import math
import numpy as np

import pyglet
from pyglet.window import key
from pyglet.gl import *

from MockVehicle import MockVehicle, MockAttitude

class Vector(np.ndarray):
    """
    Vector class that is a 3x1 numpy array with accessors called x, y, and z.
    """

    def __new__(cls, x=0.0, y=0.0, z=0.0, **kwargs):
        if isinstance(x, np.ndarray):
            # Make a deep copy and convert numpy array to Vector object.
            return np.asarray([x[0], x[1], x[2]]).view(cls)

        obj = np.ndarray.__new__(cls, shape=3, **kwargs)
        obj[0] = x
        obj[1] = y
        obj[2] = z
        return obj

    @property
    def x(self):
        return self[0]

    @x.setter
    def x(self, value):
        self[0] = value

    @property
    def y(self):
        return self[1]

    @y.setter
    def y(self, value):
        self[1] = value

    @property
    def z(self):
        return self[2]

    @z.setter
    def z(self, value):
        self[2] = value

# Based on ideas from https://pyglet.googlecode.com/hg/examples/opengl.py and 
# https://greendalecs.wordpress.com/2012/04/21/3d-programming-in-python-part-1/
# and https://github.com/holocronweaver/globe/blob/master/globe.py and 
# http://www.morrowland.com/apron/tutorials/gl/gl_camera_3b.zip
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
        """
        Start the viewer application.
        This sets up the viewer and the window.
        We then let pyglet take over the current thread for drawing and handling events.
        """
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

        self._reset_camera()
        self._reset_movement()

        self._load_objects()

    def _load_objects(self):
        """
        Initialize the simulated objects from the environment for drawing.
        We convert the objects to GL standards and give each object a color.
        """
        max_points = self.settings.get("max_points")
        self.points = deque(maxlen=max_points)
        self.quadrics = deque(maxlen=max_points)
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
        """
        Convert a sequence of Location points to GL standards.
        The returned tuple contains the points in this coordinate system.
        """
        return tuple(self._convert_point(p) for p in points)

    def _convert_point(self, p):
        """
        Convert a point Location object `p` to GL standards.
        The returned list contains the point location in this coordinate system.
        """
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

    def _reset_camera(self):
        """
        Resets the camera location and rotation vectors.

        This does not actually update the vehicle location stored in the mock vehicle and environment.
        """

        # Camera location and rotation vectors
        self.pos = Vector(0.0, 0.0, 0.0)

        self.look = Vector(0.0, 0.0, 1.0)
        self.up = Vector(0.0, 1.0, 0.0)
        self.right = Vector(1.0, 0.0, 0.0)

        self.rotation = Vector(0.0, 0.0, 0.0)
        self.old_rotation = Vector(0.0, 0.0, 0.0)

    def _reset_movement(self):
        """
        Reset vectors that control the current rotation and movement changes.
        """

        # Orientation (rotation change)
        self.orient = Vector(0.0, 0.0, 0.0)

        # Movement (translation change)
        self.strafe = Vector(0.0, 0.0, 0.0)

    def get_update_location(self, dt):
        strafe_look = dt * self.strafe.z * self.look
        strafe_up = dt * self.strafe.y * self.up
        strafe_right = dt * self.strafe.x * self.right

        move = strafe_look + strafe_up + strafe_right

        return self.environment.get_location(move.z, move.x, move.y)

    def update(self, dt):
        """
        Update the current location and rotation of the camera.

        This can be called using pyglet's scheduling system by adding it as a callback there, or directly in order to force a change.
        The given `dt` indicates the time in seconds that has passed since the last call to `update`. It can also be `0.0` to skip movement and rotation changes, or `1.0` to do exactly one step of them.
        """

        location = self.get_update_location(dt)
        self.pos.z, self.pos.x, self.pos.y = self.geometry.diff_location_meters(self.initial_location, location)

        # Now perform any rotation changes
        self.rotation.x = (self.rotation.x + dt * self.orient.x) % 360
        self.rotation.y = (self.rotation.y + dt * self.orient.y) % 360
        self.rotation.z = (self.rotation.z + dt * self.orient.z) % 360

        self._update_camera()

    def _rotate_2D(self, angle, M):
        """
        Perform a 2D rotation of a given `angle` on a matrix `M`.
        """

        cos_a = math.cos(angle * math.pi/180)
        sin_a = math.sin(angle * math.pi/180)
        R = np.array([
            [cos_a, -sin_a],
            [sin_a, cos_a]
        ])
        return np.dot(R, M)

    def _update_camera(self):
        """
        Update camera vectors based on current rotation changes.
        """

        dRot = self.rotation - self.old_rotation

        up, right = self._rotate_2D(dRot.z, np.array([self.up, self.right]))
        look, up = self._rotate_2D(dRot.x, np.array([self.look, up]))
        right, look = self._rotate_2D(dRot.y, np.array([right, look]))

        # Perform normalization of the new vectors
        look = look / np.linalg.norm(look)
        up = np.cross(look, right)
        up = up / np.linalg.norm(up)
        right = np.cross(up, look)
        right = right / np.linalg.norm(right)

        self.look = Vector(look)
        self.up = Vector(up)
        self.right = Vector(right)

        self.old_rotation = Vector(self.rotation)

    def _draw_polygon(self, face, i=-1, j=-1):
        """
        Draw a polygon based on a `face` sequence of converted points.
        """
        glBegin(GL_POLYGON)
        for p in face:
            glVertex3f(*p)
        glEnd()

    def add_point(self, point):
        """
        Add a point to be drawn in the environment.
        The given `point` is a Location object of the point to be drawn.
        """
        self.points.append(self._convert_point(point))
        self.quadrics.append(gluNewQuadric())

    def on_expose(self):
        # Dummy method that is necessary to draw when starting pyglet.
        pass

    def on_draw(self):
        """
        Draw the environment frame as seen by the camera.
        """
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw outlines only
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glLoadIdentity()
        view = self.look + self.pos
        gluLookAt(self.pos.x, self.pos.y, -self.pos.z,
                  view.x, view.y, -view.z,
                  self.up.x, self.up.y, -self.up.z)

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

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glColor3f(1, 0, 0)
        i = 0
        for point in self.points:
            glPushMatrix()
            glTranslatef(*point)
            gluSphere(self.quadrics[i], 0.05, 30, 30)
            glPopMatrix()
            i = i + 1

    def on_resize(self, width, height):
        """
        Handle a resize of the window.
        The `width` and `height` are the new window dimensions.
        """
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

        self.current_object = -1
        self.current_face = -1

    def _draw_polygon(self, face, i=-1, j=-1):
        if i != -1 and j != -1:
            if i == self.current_object and (self.current_face == -1 or j == self.current_face):
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            else:
                for sensor in self.sensors:
                    edge = sensor.get_current_edge()
                    if isinstance(edge, list) and edge[0] == i and edge[1] == j:
                        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                        break

        super(Viewer_Interactive, self)._draw_polygon(face, i, j)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    def update(self, dt):
        location = self.get_update_location(dt)
        if self.is_mock:
            try:
                self.vehicle.location = location
            except RuntimeError:
                return

        super(Viewer_Interactive, self).update(dt)

        if self.is_mock:
            pitch = math.asin(-self.look.y)
            yaw = math.atan2(self.look.x, self.look.z)
            self.vehicle.attitude = MockAttitude(pitch, yaw, 0.0)

        self.points = []
        i = 0
        for sensor in self.sensors:
            yaw = sensor.get_angle()
            pitch = sensor.get_pitch()
            sensor_distance = sensor.get_distance()
            loc = self.geometry.get_location_angle(location, sensor_distance, yaw, pitch)
            self.add_point(loc)
            print("Sensor {} distance: {} m (yaw {}, pitch {})".format(i, sensor_distance, yaw, pitch))
            i = i + 1

    def on_key_press(self, symbol, modifiers):
        if symbol == key.LEFT or symbol == key.A: # strafe left
            self.strafe.x = -self.camera_speed
        elif symbol == key.RIGHT or symbol == key.D: # strafe right
            self.strafe.x = self.camera_speed
        elif symbol == key.DOWN: # downward
            self.strafe.y = -self.camera_speed
        elif symbol == key.UP: # upward
            self.strafe.y = self.camera_speed
        elif symbol == key.NUM_SUBTRACT or symbol == key.S: # outward
            self.strafe.z = -self.camera_speed
        elif symbol == key.NUM_ADD or symbol == key.W: # inward
            self.strafe.z = self.camera_speed
        elif symbol == key.I: # rotate up
            self.orient.x = -self.rotate_speed
        elif symbol == key.K: # rotate down
            self.orient.x = self.rotate_speed
        elif symbol == key.J: # rotate left
            self.orient.y = -self.rotate_speed
        elif symbol == key.L: # rotate right
            self.orient.y = self.rotate_speed
        elif symbol == key.R: # reset location
            self.vehicle.location = self.initial_location
            self._reset_camera()
        elif symbol == key.C: # reload objects and colors
            self._load_objects()
        elif symbol == key.O: # select object
            self.current_object = self.current_object + 1
            self.current_face = -1
            if self.current_object > len(self.objects):
                self.current_object = -1
            self._update_tracking()
        elif symbol == key.P: # select plane
            self.current_face = self.current_face + 1
            if self.current_face > len(self.objects[self.current_object]):
                self.current_face = -1
            self._update_tracking()
        elif symbol == key.F: # toggle flying through objects
            if self.vehicle.get_location_callback():
                self.vehicle.unset_location_callback()
                print("Enabled flying through objects")
            else:
                self.vehicle.set_location_callback(self.environment.check_location)
                print("Disabled flying through objects")
        elif symbol == key.Q: # quit
            pyglet.app.exit()
            return
        else:
            return

        pyglet.clock.schedule(self.update)
        # Ensure update function is called immediately and not have a large 
        # time delta caused by delay for the first update.
        pyglet.clock.get_default().update_time()
        pyglet.clock.tick()

    def _update_tracking(self):
        for sensor in self.sensors:
            sensor.current_object = self.current_object
            sensor.current_face = self.current_face

    def on_key_release(self, symbol, modifiers):
        self._reset_movement()
        pyglet.clock.unschedule(self.update)

    def on_mouse_scroll(self, x, y, dx, dy):
        # Move into/outward
        self.strafe.z = dy
        self.update(1.0)
        self._reset_movement()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        # dx is horizontal change of mouse position, dy is vertical change.
        # We want to rotate around the y axis (vertical altitude, yaw) upon 
        # horizontal change and around the x axis (horizontal on plane, pitch) 
        # upon vertical change.
        mx = (self.rotate_speed / self.win.height) * dy
        my = (self.rotate_speed / self.win.width) * dx
        self.rotation.x = self.rotation.x - mx
        self.rotation.y = self.rotation.y + my
        self._update_camera()

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

        self.rotation.y = self.environment.get_yaw() * 180/math.pi
        super(Viewer_Vehicle, self).update(0.0)
