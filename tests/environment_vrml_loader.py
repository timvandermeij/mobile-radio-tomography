from ..environment.VRML_Loader import VRML_Loader
from environment import EnvironmentTestCase

class TestEnvironmentVRMLLoader(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle"
        ], use_infrared_sensor=False)

        super(TestEnvironmentVRMLLoader, self).setUp()

    def test_initialization(self):
        filename = "tests/vrml/castle.wrl"
        # Translation must have correct length.
        with self.assertRaises(ValueError):
            loader = VRML_Loader(self.environment, filename, translation=[1, 2])

        loader = VRML_Loader(self.environment, filename, translation=[1, 2, 3])
        self.assertEqual(loader.environment, self.environment)
        self.assertEqual(loader.filename, filename)
        self.assertEqual(loader.translation, (1, 2, 3))

    def test_get_objects(self):
        filename = "tests/vrml/castle.wrl"
        loader = VRML_Loader(self.environment, filename,
                             translation=[40.0, 3.14, 5.67])
        self.assertEqual(len(loader.get_objects()), 14)

        loader = VRML_Loader(self.environment, "tests/vrml/deranged_house.wrl")
        self.assertEqual(loader.translation, (0, 0, 0))
        self.assertEqual(len(loader.get_objects()), 2)

        loader = VRML_Loader(self.environment, "tests/vrml/inline.wrl")
        self.assertEqual(loader.translation, (0, 0, 0))
        self.assertEqual(len(loader.get_objects()), 15)
