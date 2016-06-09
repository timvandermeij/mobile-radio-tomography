from ..environment.VRMLLoader import VRMLLoader
from environment import EnvironmentTestCase

class TestVRMLLoader(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle"
        ], use_infrared_sensor=False)

        super(TestVRMLLoader, self).setUp()

    def test_load(self):
        filename = "tests/vrml/castle.wrl"

        with self.assertRaises(ValueError):
            loader = VRMLLoader(self.environment, filename, translation=[1, 2])

        loader = VRMLLoader(self.environment, filename, translation=[40.0, 3.14, 5.67])
        self.assertEqual(loader.filename, filename)
        self.assertEqual(loader.translation, (40.0, 3.14, 5.67))
        self.assertEqual(len(loader.get_objects()), 14)

        loader = VRMLLoader(self.environment, "tests/vrml/deranged_house.wrl")
        self.assertEqual(loader.translation, (0, 0, 0))
        self.assertEqual(len(loader.get_objects()), 2)

        loader = VRMLLoader(self.environment, "tests/vrml/inline.wrl")
        self.assertEqual(loader.translation, (0, 0, 0))
        self.assertEqual(len(loader.get_objects()), 15)
