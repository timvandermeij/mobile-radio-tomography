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

        for name, thread in self.threads.items():
            thread.deactivate()
