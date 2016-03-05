import thread

class Threadable(object):
    def __init__(self, name, thread_manager):
        """
        Initialize the threadable object.
        """

        self.name = name
        self.thread_manager = thread_manager

    def activate(self):
        """
        Activate the threadable object.
        """

        self.thread_manager.register(self.name, self)

    def deactivate(self):
        """
        Deactivate the threadable object.
        """

        self.thread_manager.unregister(self.name)

    def interrupt(self):
        """
        Interrupt the main thread.
        """

        thread.interrupt_main()
