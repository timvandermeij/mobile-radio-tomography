from OpenGLContext.loaders.loader import Loader
from vrml.vrml97 import basenodes, nodetypes

class VRMLLoader(object):
    def __init__(self, environment, filename):
        self.environment = environment
        self.filename = filename
        self.scene = Loader.load(self.filename)
        self.objects = None

    def get_objects(self):
        if self.objects is None:
            self.objects = []
            self.get_children(self.scene)

        return self.objects

    def get_children(self, group):
        for child in group.children:
            if isinstance(child, nodetypes.Grouping):
                self.get_children(child)
            elif isinstance(child, basenodes.Shape):
                self.get_geometry(child.geometry)
            elif isinstance(child, nodetypes.Children):
                print(type(child), child)
            else:
                print("Other type: ", type(child))

    def get_geometry(self, geometry):
        faces = []
        face = []
        for i in geometry.coordIndex:
            if i == -1:
                faces.append(face)
                face = []
                pass
            else:
                point = geometry.coord.point[i]
                # Convert to Location
                # point notation is in (x,y,z) where y is the verticlal axis. 
                # We have to convert it to (x,z,y) since the first two are 
                # related to distances on the ground (lat/lon) and the y axis 
                # is related to altitude offset.
                point[1],point[2] = point[2],point[1]
                loc = self.environment.get_location(point)
                face.append(loc)

        self.objects.append(faces)
