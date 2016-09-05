import os
import sys
import unittest
from mock import patch, Mock
from ..core import Import_Manager

class TestCoreImportManager(unittest.TestCase):
    def setUp(self):
        self.import_manager = Import_Manager.Import_Manager()

        # Base package that the import manager uses. We expect it to be equal 
        # to the base directory name.
        path = os.path.dirname(os.path.dirname(__file__))

        self.package = os.path.basename(path)

        self.module_name = self.package + ".mock_module"
        self.sub_module_name = self.package + ".sub"
        self.relative_module_name = self.package + ".sub.Relative"
        self.global_module_name = "global_module"

        self.mock_module = Mock(__name__=self.module_name, Mock_Class=Mock(),
                                spec=True)

        self.mock_sub_module = Mock(__name__=self.sub_module_name, spec=True)
        self.mock_relative_module = Mock(__name__=self.relative_module_name,
                                         Relative=Mock(), Second_Class=Mock(),
                                         spec=True)
        self.mock_global_module = Mock(__name__=self.global_module_name,
                                       spec=True)

        modules = {
            self.module_name: self.mock_module,
            self.sub_module_name: self.mock_sub_module,
            self.relative_module_name: self.mock_relative_module,
            self.global_module_name: self.mock_global_module
        }

        self._import_patcher = patch.dict('sys.modules', modules)
        self._import_patcher.start()

    def tearDown(self):
        self._import_patcher.stop()

    def test_initialization(self):
        self.assertEqual(self.import_manager._package, self.package)
        self.assertEqual(self.import_manager._unloaded_modules, {})

    def test_package(self):
        self.assertEqual(self.import_manager.package, self.package)

    def test_load(self):
        self.assertEqual(self.import_manager.load("mock_module"),
                         self.mock_module)
        self.assertEqual(self.import_manager.load("Relative", relative_module="sub"), self.mock_relative_module)
        self.assertEqual(self.import_manager.load("global_module", relative=False), self.mock_global_module)

        with self.assertRaises(ImportError):
            self.import_manager.load("nonexistent_module", relative=True)

    def test_load_class(self):
        # Load a class from a module.
        loaded_class = self.import_manager.load_class("Mock_Class",
                                                      module="mock_module")
        self.assertEqual(loaded_class, self.mock_module.Mock_Class)

        # Load a class from a relative submodule.
        loaded_sub_class = self.import_manager.load_class("Relative",
                                                          relative_module="sub")
        self.assertEqual(loaded_sub_class, self.mock_relative_module.Relative)

        # Load a class from a relative submodule with a different name than the 
        # module.
        other_class = self.import_manager.load_class("Second_Class",
                                                     module="Relative",
                                                     relative_module="sub")
        self.assertEqual(other_class, self.mock_relative_module.Second_Class)

        # Import errors are generated correctly.
        with self.assertRaises(ImportError):
            self.import_manager.load_class("sys", module="nonexistent_module")

        error_msg = ".*'Nonexistent' from module '{}'".format(self.module_name)
        with self.assertRaisesRegexp(ImportError, error_msg):
            self.import_manager.load_class("Nonexistent", module="mock_module")

    def test_unload(self):
        self.import_manager.unload("mock_module", relative=True)
        self.assertNotIn(self.module_name, sys.modules)

        self.import_manager.unload("global_module", relative=False)
        self.assertNotIn(self.global_module_name, sys.modules)

    def test_reload(self):
        # We can reload the Import_Manager module without breaking.
        new_manager = self.import_manager.reload("core.Import_Manager")
        self.assertEqual(new_manager.__name__,
                         self.package + ".core.Import_Manager")
        self.assertEqual(self.import_manager.reload(Import_Manager).__name__,
                         self.package + ".core.Import_Manager")

        self.import_manager.reload(unittest)
        self.assertIn("unittest", sys.modules)

        # A module that was not yet loaded cannot be reloaded.
        with self.assertRaises(ImportError):
            self.import_manager.reload("nonexistent_module")

    def test_reload_unloaded(self):
        self.import_manager.unload("mock_module")
        self.assertEqual(self.import_manager.reload_unloaded("mock_module"),
                         self.mock_module)

        self.import_manager.unload("global_module", relative=False)
        self.assertEqual(self.import_manager.reload_unloaded("global_module", relative=False),
                         self.mock_global_module)

        # We can unload and reload the Import_Manager module without breaking.
        self.import_manager.unload("core.Import_Manager")
        self.import_manager.reload_unloaded("core.Import_Manager")

        # A module that was not unloaded cannot be reloaded.
        with self.assertRaises(ImportError):
            self.import_manager.reload_unloaded("sub.Relative", relative=True)

        # A module that has already been reloaded cannot be reloaded again.
        with self.assertRaises(ImportError):
            self.import_manager.reload_unloaded("mock_module", relative=True)
