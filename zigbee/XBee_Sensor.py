class XBee_Sensor(object):
    def activate(self):
        raise NotImplementedError("Subclasses must override activate()")

    def deactivate(self):
        raise NotImplementedError("Subclasses must override deactivate()")

    def enqueue(self, packet):
        raise NotImplementedError("Subclasses must override enqueue(packet)")

    def _send(self):
        raise NotImplementedError("Subclasses must override _send()")

    def _receive(self, packet):
        raise NotImplementedError("Subclasses must override _receive(packet)")
