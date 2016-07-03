import os
import numpy as np
from vrml.vrml97 import basenodes, nodetypes, parser, parseprocessor

class VRML_Loader(object):
    """
    Parser for VRML files. The VRML language is described in its specification
    at http://www.web3d.org/documents/specifications/14772/V2.0/index.html
    """

    def __init__(self, environment, filename, translation=None, transform=None):
        self.environment = environment
        self.filename = filename

        if translation is None:
            translation = (0.0, 0.0, 0.0)
        elif len(translation) != 3:
            raise ValueError("Translation must be a 3-component offset")

        self.translation = tuple(translation)
        self._transform = transform

        vrml_parser = parser.Parser(parser.grammar, "vrmlFile")
        processor = parseprocessor.ParseProcessor(baseURI=self.filename)
        with open(self.filename, 'r') as f:
            data = f.read()
            self._scene = vrml_parser.parse(data, processor=processor)[1][1]

        self._objects = None

    def get_objects(self):
        """
        Retrieve the objects from the VRML scene file.

        The objects are provided as a list of lists of lists, where the deepest
        nested lists are faces describing a polygon using point locations. Each
        element of the list can therefore have multiple faces.
        """

        if self._objects is None:
            self._objects = []
            self._parse_children(self._scene, self._transform)

        return self._objects

    def _parse_children(self, group, transform=None):
        for child in group.children:
            if isinstance(child, basenodes.Inline):
                # Include the objects from the referenced file into the scene.
                path = os.path.join(os.path.dirname(self.filename),
                                    child.url[0])
                loader = VRML_Loader(self.environment, path,
                                     translation=self.translation,
                                     transform=transform)
                self._objects.extend(loader.get_objects())
            elif isinstance(child, basenodes.Transform):
                # Jumble up transformation matrices, in case they are nested.
                forward = child.localMatrices().data[0]
                if forward is not None:
                    if transform is not None:
                        new_transform = np.dot(transform, forward)
                    else:
                        new_transform = forward
                else:
                    new_transform = transform

                self._parse_children(child, new_transform)
            elif isinstance(child, nodetypes.Grouping):
                # Retrieve children from grouped nodes.
                self._parse_children(child, transform)
            elif isinstance(child, basenodes.Shape):
                # Parse the coordinates from a shape's geometry.
                self._parse_geometry(child.geometry, transform)

    def _parse_geometry(self, geometry, transform=None):
        faces = []
        face = []
        for i in geometry.coordIndex:
            if i == -1:
                faces.append(face)
                face = []
            else:
                point = geometry.coord.point[i]
                if transform is not None:
                    # The translation matrices from the VRML library are for 
                    # affine translations, but they are transposed for some 
                    # reason. See vrml.vrml97.transformmatrix, e.g. line 319.
                    point = np.dot(transform.T, np.append(point, 1).T)

                # Convert to Location
                # VRML geometry notation is in (x,z,y) where y is the vertical 
                # axis (using GL notation here). We have to convert it to 
                # (z,x,y) since the z/x are related to distances on the ground 
                # in north and east directions, respectively, and y is still 
                # the altitude.
                north = point[1] + self.translation[0]
                east = point[0] - self.translation[1]
                alt = point[2] + self.translation[2]
                loc = self.environment.get_location(north, east, alt)
                face.append(loc)

        if len(face) > 0:
            faces.append(face)
        self._objects.append(faces)
