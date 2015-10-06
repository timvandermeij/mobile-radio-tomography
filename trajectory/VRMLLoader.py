import numpy as np
from OpenGLContext.loaders.loader import Loader
from vrml.vrml97 import basenodes, nodetypes

class VRMLLoader(object):
    """
    VRML parser.
    The VRML language is described in its specification at http://www.web3d.org/documents/specifications/14772/V2.0/index.html
    """

    def __init__(self, environment, filename):
        # TODO: Allow setting a global transform so that we can place objects 
        # away from the starting location
        self.environment = environment
        self.filename = filename
        self.scene = Loader.load(self.filename)
        self.objects = None

    def get_objects(self):
        if self.objects is None:
            self.objects = []
            self._parse_children(self.scene)

        return self.objects

    def _parse_children(self, group, transform=None):
        for child in group.children:
            if isinstance(child, basenodes.Inline):
                loader = VRMLLoader(self.environment, child.url)
                self.objects.extend(loader.get_objects())
            elif isinstance(child, nodetypes.Transforming):
                # Jumble up transformation matrices
                try:
                    forward = child.localMatrices().data[0]
                    if forward is not None:
                        if transform is not None:
                            transform = np.dot(transform, forward)
                        else:
                            transform = forward
                except NotImplemented:
                    transform = forward

                self._parse_children(child, transform)
            elif isinstance(child, nodetypes.Grouping):
                self._parse_children(child, transform)
            elif isinstance(child, basenodes.Shape):
                self._parse_geometry(child.geometry, transform)
            elif isinstance(child, nodetypes.Children):
                print(type(child), child)
            else:
                print("Other type: ", type(child))

    def _parse_geometry(self, geometry, transform=None):
        faces = []
        face = []
        for i in geometry.coordIndex:
            if i == -1:
                faces.append(face)
                face = []
                pass
            else:
                point = geometry.coord.point[i]
                if transform is not None:
                    # The translation matrices from the VRML library are for 
                    # affine translations, but they are transposed for some 
                    # reason. See vrml.vrml87.transformmatrix, e.g. line 319.
                    point = np.dot(transform.T, np.append(point, 1).T)

                # Convert to Location
                # point notation is in (x,y,z) where y is the verticlal axis. 
                # We have to convert it to (x,z,y) since the first two are 
                # related to distances on the ground (lat/lon) and the y axis 
                # is related to altitude offset.
                loc = self.environment.get_location(point[0], point[2], point[1])
                face.append(loc)

        if len(face) > 0:
            faces.append(face)
        self.objects.append(faces)
