import unittest
from ..settings import Settings

class TestSettings(unittest.TestCase):
    def test_existing_key(self):
        settings = Settings("tests/settings.json", "foo")
        self.assertEqual(settings.get("bar"), 2)
        self.assertEqual(settings.get("baz"), True)

    def test_missing_key(self):
        settings = Settings("tests/settings.json", "foo")
        with self.assertRaises(KeyError):
            settings.get("qux")

    def test_missing_file(self):
        with self.assertRaises(IOError):
            settings = Settings("tests/invalid.json", "foo")
