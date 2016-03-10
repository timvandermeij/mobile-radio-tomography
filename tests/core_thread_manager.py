import unittest
from mock import patch
from ..core.Threadable import Threadable
from ..core.Thread_Manager import Thread_Manager

class ThreadableTestCase(unittest.TestCase):
    """
    A test case that makes use of Threadable. We make sure that
    all spawned threads are destroyed after the test.
    """

    def tearDown(self):
        super(ThreadableTestCase, self).tearDown()

        if hasattr(self, "thread_manager"):
            self.thread_manager.destroy()

        if hasattr(self, "environment") and hasattr(self.environment, "thread_manager"):
            self.environment.thread_manager.destroy()

class Mock_Thread(Threadable):
    def __init__(self, thread_manager):
        super(Mock_Thread, self).__init__("mock_thread", thread_manager)

    def activate(self):
        super(Mock_Thread, self).activate()

    def deactivate(self):
        super(Mock_Thread, self).deactivate()

class TestCoreThreadManager(ThreadableTestCase):
    def setUp(self):
        # Initialize the thread manager.
        self.thread_manager = Thread_Manager()

    def test_initialization(self):
        # Initially the thread storage must be empty.
        self.assertEqual(self.thread_manager._threads, {})

    def test_register(self):
        # The thread storage must contain a registered thread.
        mock_thread = Mock_Thread(self.thread_manager)
        self.thread_manager.register("mock_thread", mock_thread)
        self.assertEqual(self.thread_manager._threads, {
            "mock_thread": mock_thread
        })

    def test_unregister(self):
        # The thread storage must not contain an unregistered thread.
        mock_thread = Mock_Thread(self.thread_manager)
        self.thread_manager.register("mock_thread", mock_thread)
        self.thread_manager.unregister("mock_thread")
        self.assertEqual(self.thread_manager._threads, {})

        # Unregistering a nonexistent thread must not cause an error.
        self.thread_manager.unregister("nonexistent_thread")

    def test_destroy_storage_empty(self):
        # After destruction the thread storage must be empty.
        mock_thread = Mock_Thread(self.thread_manager)
        self.thread_manager.register("mock_thread", mock_thread)
        self.assertNotEqual(self.thread_manager._threads, {})
        self.thread_manager.destroy()
        self.assertEqual(self.thread_manager._threads, {})

    @patch.object(Mock_Thread, "deactivate")
    def test_destroy_deactivate_called(self, mock_thread_deactivate):
        # After destruction the deactivation method must be called
        # for each registered thread.
        mock_thread = Mock_Thread(self.thread_manager)
        self.thread_manager.register("mock_thread", mock_thread)
        self.thread_manager.destroy()
        self.assertTrue(mock_thread_deactivate.called)
