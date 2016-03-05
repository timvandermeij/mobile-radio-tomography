import datetime
import logging

class Thread_Manager(object):
    def __init__(self):
        """
        Initialize the thread manager.
        """

        self.threads = {}

    def register(self, name, thread):
        """
        Register a thread.
        """

        self.threads[name] = thread

    def unregister(self, name):
        """
        Unregister a thread.
        """

        if name not in self.threads:
            return

        del self.threads[name]

    def destroy(self):
        """
        Destroy all registered threads by deactivating them.
        """

        self.log("main thread")
        for name, thread in self.threads.items():
            thread.deactivate()

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
