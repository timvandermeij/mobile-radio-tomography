class Threadable(object):
    def __init__(self, name, thread_manager):
        """
        Initialize the threadable object.
        """

        self._name = name
        self._thread_manager = thread_manager

    def activate(self):
        """
        Activate the threadable object.
        """

        self._thread_manager.register(self._name, self)

    def deactivate(self):
        """
        Deactivate the threadable object.
        """

        self._thread_manager.unregister(self._name)

    def interrupt(self):
        """
        Interrupt the main thread.
        """
        self._thread_manager.interrupt(self._name)
