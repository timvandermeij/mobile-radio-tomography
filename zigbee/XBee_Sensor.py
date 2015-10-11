class XBee_Sensor(object):
    def activate(self):
        raise NotImplementedError("Subclasses must override activate()")

    def deactivate(self):
        raise NotImplementedError("Subclasses must override deactivate()")

    def _send(self):
        raise NotImplementedError("Subclasses must override _send()")

    def _receive(self, packet):
        raise NotImplementedError("Subclasses must override _receive()")

    def _get_location(self):
        raise NotImplementedError("Subclasses must override _get_location()")
