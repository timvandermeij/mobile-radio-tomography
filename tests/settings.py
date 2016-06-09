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
            Settings("tests/settings/invalid.json", "foo")

        with self.assertRaises(IOError):
            Settings("tests/settings/settings.json", "foo",
                     defaults_file="tests/settings/invalid.json")

    def test_missing_component(self):
        with self.assertRaises(KeyError):
            Settings("tests/settings/settings.json", "invalid",
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
        # The exception mentions the missing setting and the component.
        with self.assertRaisesRegexp(KeyError, "'qux'.*'foo'"):
            settings.get("qux")

    def test_missing_parent_key(self):
        settings = Settings("tests/settings/empty.json", "child",
                            defaults_file="tests/settings/defaults.json")
        # The exception mentions the current component rather than the parent.
        with self.assertRaisesRegexp(KeyError, "'qux'.*'child'"):
            settings.get("qux")

    def test_get_parent(self):
        settings = Settings("tests/settings/empty.json", "child",
                            defaults_file="tests/settings/defaults.json")
        self.assertEqual(settings.get("bar"), 2)
        self.assertEqual(settings.get("baz"), False)

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
            "items": [1, 2, 3],
            "select": "b"
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
                "value": 2,
                "min": 1,
                "max": 42
            },
            "baz": {
                "type": "bool",
                "default": True,
                "value": True
            },
            "long_name": {
                "type": "string",
                "default": "some_text",
                "value": "new_text",
                "required": True
            },
            "items": {
                "type": "list",
                "default": [1, 2, 3],
                "value": [1, 2, 3],
                "subtype": "int"
            },
            "select": {
                "type": "string",
                "choices": ["a", "b", "c"],
                "default": "b",
                "value": "b",
                "required": False
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
        expected = set(("bar", "baz", "long_name", "items", "select"))
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

    def test_set_parent(self):
        parent_settings = Settings("tests/settings/empty.json", "foo",
                                   defaults_file="tests/settings/defaults.json")
        child_settings = Settings("tests/settings/empty.json", "child",
                                  defaults_file="tests/settings/defaults.json")
        child_settings.set("bar", 3)
        self.assertEqual(parent_settings.get("bar"), 3)
        self.assertEqual(child_settings.get("bar"), 3)

        child_settings.set("baz", False)
        self.assertEqual(parent_settings.get("baz"), True)
        self.assertEqual(child_settings.get("baz"), False)

    def test_nonexistent_set(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        # The exception mentions the missing setting and the component.
        with self.assertRaisesRegexp(KeyError, "'new'.*'foo'"):
            settings.set("new", "added")

    def test_nonexistent_parent_set(self):
        settings = Settings("tests/settings/settings.json", "child",
                            defaults_file="tests/settings/defaults.json")
        # The exception mentions the current component rather than the parent.
        with self.assertRaisesRegexp(KeyError, "'new'.*'child'"):
            settings.set("new", "added")

    def test_empty_set(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        with self.assertRaisesRegexp(ValueError, "nonempty"):
            settings.set("long_name", "")

        # Non-required settings can be set to empty value.
        settings.set("select", "")

    def test_min_max_set(self):
        settings = Settings("tests/settings/settings.json", "foo",
                            defaults_file="tests/settings/defaults.json")
        with self.assertRaisesRegexp(ValueError, "at least 1"):
            settings.set("bar", 0)
        with self.assertRaisesRegexp(ValueError, "at most 42"):
            settings.set("bar", 100)

    def test_format_set(self):
        settings = Settings("tests/settings/settings.json", "child",
                            defaults_file="tests/settings/defaults.json")
        settings.set("test", "empty")
        self.assertEqual(settings.get("test"), "tests/settings/empty.json")
        settings.set("test", "tests/settings/defaults.json")
        self.assertEqual(settings.get("test"), "tests/settings/defaults.json")
        with self.assertRaisesRegexp(ValueError, "existing file"):
            settings.set("test", "invalid")

        settings.set("setters", "tests/settings/empty.json")
        self.assertEqual(settings.get("setters"), "empty")
        settings.set("setters", "defaults")
        self.assertEqual(settings.get("setters"), "defaults")
        with self.assertRaisesRegexp(ValueError, "match the format"):
            settings.set("setters", "tests/settings.py")
