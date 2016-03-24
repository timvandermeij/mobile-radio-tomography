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
        Settings.settings_files = {}

class TestSettings(SettingsTestCase):
    def test_missing_file(self):
        with self.assertRaises(IOError):
            settings = Settings("tests/settings/invalid.json", "foo")

        with self.assertRaises(IOError):
            settings = Settings("tests/settings/settings.json", "foo",
                                defaults_file="tests/settings/invalid.json")

    def test_missing_component(self):
        with self.assertRaises(KeyError):
            settings = Settings("tests/settings/settings.json", "invalid",
                                defaults_file="tests/settings/defaults.json")

    def test_name(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        self.assertEqual(settings.name, "Foo component")

    def test_existing_key(self):
        settings = Settings("tests/settings/empty.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        self.assertEqual(settings.get("bar"), 2)
        self.assertEqual(settings.get("baz"), True)
        self.assertEqual(settings.get("long_name"), "some_text")

    def test_missing_key(self):
        settings = Settings("tests/settings/empty.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        with self.assertRaises(KeyError):
            settings.get("qux")

    def test_get_override(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        self.assertEqual(settings.get("long_name"), "new_text")

    def test_get_all(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        expected = {
            "bar": 2,
            "baz": True,
            "long_name": "new_text",
            "items": [1,2,3]
        }
        for key, value in settings.get_all():
            self.assertEqual(value, expected[key])
            # Disallow key to be multiple times in iterator, and test afterward 
            # whether all keys were in there.
            del expected[key]

        self.assertEqual(expected, {})

    def test_get_info(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        expected = {
            "bar": {
                "type": "int",
                "default": 2,
                "value": 2
            },
            "baz": {
                "type": "bool",
                "default": True,
                "value": True
            },
            "long_name": {
                "type": "string",
                "default": "some_text",
                "value": "new_text"
            },
            "items": {
                "type": "list",
                "default": [1, 2, 3],
                "value": [1, 2, 3]
            }
        }
        for key, value in settings.get_info():
            self.assertEqual(value, expected[key])
            # Disallow key to be multiple times in iterator, and test afterward 
            # whether all keys were in there.
            del expected[key]

        self.assertEqual(expected, {})

    def test_keys(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        expected = set(("bar", "baz", "long_name", "items"))
        for key in settings.keys():
            self.assertIn(key, expected)
            # Disallow key to be multiple times in iterator, and test afterward 
            # whether all keys were in there.
            expected.remove(key)

        self.assertEqual(expected, set())

    def test_set(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        settings.set("bar", 3)
        self.assertEqual(settings.get("bar"), 3)

    def test_nonexistent_set(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        with self.assertRaises(KeyError):
            settings.set("new", "added")

    def test_parent(self):
        settings = Settings("tests/settings/empty.json", "child",
                            defaults_file="tests/settings/defaults.json")
        self.assertEqual(settings.get("bar"), 2)
        self.assertEqual(settings.get("baz"), False)
        # Test: Exception should still mention child component
        with self.assertRaisesRegexp(KeyError, "'child'"):
            settings.get("qux")
