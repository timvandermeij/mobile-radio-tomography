import datetime
import logging
import sys
import thread

class Thread_Manager(object):
    def __init__(self):
        """
        Initialize the thread manager.
        """

        self._threads = {}

    def register(self, name, thread):
        """
        Register a thread.
        """

        self._threads[name] = thread

    def unregister(self, name):
        """
        Unregister a thread.
        """

        if name not in self._threads:
            return

        del self._threads[name]

    def destroy(self):
        """
        Destroy all registered threads by deactivating them.
        """

        # Log the destroy call only if it is being called from an except clause
        # to prevent "None" spam in the logs.
        if sys.exc_info() != (None, None, None):
            self.log("main thread")

        for name, thread in self._threads.items():
            thread.deactivate()

    def interrupt(self, name):
        """
        Handle an exception on a registered thread.

        This method interrupts the main thread and logs the exception.
        """

        self.log("'{}' thread".format(name))

        # Do not interrupt the main thread if the thread is not registered.
        # This prevents stale threads that have long been deactivated and 
        # unregistered from causing interrupts or segmentation faults.
        if name in self._threads:
            thread.interrupt_main()

    def log(self, source):
        """
        Log an exception from a source (either the main thread or
        a custom spawned thread) in the log file.
        """

        if not hasattr(self, "_logger"):
            # Lazily initialize the logger.
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

            file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            file_handler = logging.FileHandler("logs/{}.log".format(file_name))
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)

            self._logger = logging.getLogger()
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(file_handler)

        self._logger.exception(source)
