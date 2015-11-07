class XBee_Sensor(object):
    def activate(self):
        raise NotImplementedError("Subclasses must implement activate()")

    def deactivate(self):
        raise NotImplementedError("Subclasses must implement deactivate()")

    def enqueue(self, packet, to=None):
        raise NotImplementedError("Subclasses must implement enqueue(packet, to=None)")

    def _send(self):
        raise NotImplementedError("Subclasses must implement _send()")

    def _receive(self, packet):
        raise NotImplementedError("Subclasses must implement _receive(packet)")
