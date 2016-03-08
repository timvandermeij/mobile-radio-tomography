import unittest
from ..settings import Settings

class SettingsTestCase(unittest.TestCase):
    """
    A test case that makes use of Arguments or Settings.
    These tests should always clean up the static state of Settings so that
    any changes made in the Settings objects do not bleed through into other
    tests, which could cause intermittent passes or fails depending on the
    test running order.
    """

    def tearDown(self):
        super(SettingsTestCase, self).tearDown()
        print("Tearing down settings for '{}'".format(self.__class__.__name__))
        Settings.settings_files = {}

class TestSettings(SettingsTestCase):
    def test_missing_file(self):
        with self.assertRaises(IOError):
            settings = Settings("tests/invalid.json", "foo")

    def test_missing_component(self):
        with self.assertRaises(KeyError):
            settings = Settings("tests/settings.json", "invalid")

    def test_name(self):
        settings = Settings("tests/settings.json", "foo")
        self.assertEqual(settings.name, "Foo component")

    def test_existing_key(self):
        settings = Settings("tests/settings.json", "foo")
        self.assertEqual(settings.get("bar"), 2)
        self.assertEqual(settings.get("baz"), True)

    def test_missing_key(self):
        settings = Settings("tests/settings.json", "foo")
        with self.assertRaises(KeyError):
            settings.get("qux")

    def test_get_all(self):
        settings = Settings("tests/settings.json", "foo")
        expected = {
            "bar": 2,
            "baz": True,
            "long_name": "some_text",
            "items": [1,2,3]
        }
        for key, value in settings.get_all():
            self.assertEqual(value, expected[key])
            # Disallow key to be multiple times in iterator, and test afterward 
            # whether all keys were in there.
            del expected[key]

        self.assertEqual(expected, {})

    def test_set(self):
        settings = Settings("tests/settings.json", "foo")
        settings.set("bar", 3)
        settings.set("new", "added")
        self.assertEqual(settings.get("bar"), 3)
        self.assertEqual(settings.get("new"), "added")

    def test_parent(self):
        settings = Settings("tests/settings.json", "child")
        self.assertEqual(settings.get("bar"), 2)
        self.assertEqual(settings.get("baz"), False)
        # Test: Exception should still mention child component
        with self.assertRaisesRegexp(KeyError, "'child'"):
            settings.get("qux")
