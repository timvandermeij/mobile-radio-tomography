class XBee_Sensor(object):
    def activate(self):
        raise NotImplementedError("Subclasses must override activate()")

    def _send(self):
        raise NotImplementedError("Subclasses must override _send()")

    def _receive(self):
        raise NotImplementedError("Subclasses must override _receive()")
