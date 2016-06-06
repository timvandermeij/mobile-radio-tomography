import logging
import thread
import threading
import unittest
from mock import patch, call, Mock, MagicMock
from ..core.Threadable import Threadable
from ..core.Thread_Manager import Thread_Manager

class ThreadableTestCase(unittest.TestCase):
    """
    A base class for test cases that make use of a `Threadable` object.
    We make sure that all spawned threads are destroyed after the test.
    """

    def setUp(self):
        self._startup_threads = threading.active_count()
        self._info = []
        # Thread manager object must be provided by the extending test case 
        # classes.
        self.thread_manager = None

        super(ThreadableTestCase, self).setUp()

    def tearDown(self):
        if not hasattr(self, "_startup_threads"):
            super(ThreadableTestCase, self).tearDown()

            self.fail("setUp was not called")

        if not hasattr(self, "thread_manager"):
            super(ThreadableTestCase, self).tearDown()

            self.fail("No thread manager found")

        thread_info = ', '.join(self.thread_manager._threads.keys())
        self._info = [
            "Registered threads: {}".format(thread_info),
            "Startup threads: {}".format(self._startup_threads),
            "Running threads: {}".format(threading.active_count())
        ]

        self.thread_manager.destroy()

        super(ThreadableTestCase, self).tearDown()

        # Check whether all threads have been stopped after all the `tearDown` 
        # methods have finished.
        self.addCleanup(self.check_remaining_threads)

    def check_remaining_threads(self):
        count = threading.active_count()
        if count != self._startup_threads or self.thread_manager._threads:
            self._info.insert(0, "Threads were not cleaned up correctly.")

            thread_info = ', '.join(self.thread_manager._threads.keys())
            self._info.append("Remaining threads: {}".format(thread_info))
            self._info.append("Latent threads: {}".format(count))
            self.fail('\n'.join(self._info))

class Mock_Thread(Threadable):
    def __init__(self, thread_manager):
        super(Mock_Thread, self).__init__("mock_thread", thread_manager)

    def activate(self):
        super(Mock_Thread, self).activate()

    def deactivate(self):
        super(Mock_Thread, self).deactivate()

class TestCoreThreadManager(ThreadableTestCase):
    def setUp(self):
        super(TestCoreThreadManager, self).setUp()

        # Initialize the thread manager.
        self.thread_manager = Thread_Manager()

    def test_initialization(self):
        # Initially the thread storage must be empty.
        self.assertEqual(self.thread_manager._threads, {})

    def test_register(self):
        # The thread storage must contain a registered thread.
        mock_thread = Mock_Thread(self.thread_manager)
        self.assertEqual(mock_thread.thread_name, "mock_thread")
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

    @patch.object(Thread_Manager, 'log')
    def test_destroy_log(self, log_mock):
        # The `destroy` method does not call `log` outside an exception context.
        self.thread_manager.destroy()
        self.assertEqual(log_mock.call_count, 0)

        # If `destroy` is called in an exception handling block, `log` is called.
        try:
            raise RuntimeError("Exception must be handled in this test")
        except:
            self.thread_manager.destroy()

        log_mock.assert_called_once_with("main thread")

    @patch.object(thread, 'interrupt_main')
    @patch.object(Thread_Manager, 'log')
    def test_interrupt_unregistered(self, log_mock, interrupt_mock):
        # An unregistered thread has its error logged, but does not interrupt 
        # the main thread.
        mock_thread = Mock_Thread(self.thread_manager)
        mock_thread.interrupt()
        log_mock.assert_called_once_with("'mock_thread' thread")
        self.assertEqual(interrupt_mock.call_count, 0)

    @patch.object(thread, 'interrupt_main')
    @patch.object(Thread_Manager, 'log')
    def test_interrupt_registered(self, log_mock, interrupt_mock):
        # A registered thread has its error logged and interrupts the main thread.
        mock_thread = Mock_Thread(self.thread_manager)
        self.thread_manager.register("mock_thread", mock_thread)
        mock_thread.interrupt()
        log_mock.assert_called_once_with("'mock_thread' thread")
        self.assertEqual(interrupt_mock.call_count, 1)

    def test_log(self):
        # Test lazy initialization of logger.
        logger_mock = MagicMock()
        patcher = patch.object(logging, 'getLogger', Mock(return_value=logger_mock))
        patcher.start()
        self.assertEqual(self.thread_manager._logger, None)
        self.thread_manager.log("'foo' source")
        self.assertEqual(self.thread_manager._logger, logger_mock)
        logger_mock.setLevel.assert_called_once_with(logging.DEBUG)
        self.assertEqual(logger_mock.addHandler.call_count, 1)

        # Test that all calls are logged.
        self.thread_manager.log("'bar' source")
        self.assertEqual(logger_mock.exception.call_count, 2)
        logger_mock.exception.assert_has_calls([call("'foo' source"), call("'bar' source")])

        patcher.stop()
