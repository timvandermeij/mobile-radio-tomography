import unittest
from ..settings import Settings

class TestSettings(unittest.TestCase):
    def setUp(self):
        self.settings = Settings("tests/settings.json", "foo")

    def test_existing_key(self):
        self.assertEqual(self.settings.get("bar"), 2)
        self.assertEqual(self.settings.get("baz"), True)

    def test_missing_key(self):
        with self.assertRaises(KeyError):
            self.settings.get("qux")
