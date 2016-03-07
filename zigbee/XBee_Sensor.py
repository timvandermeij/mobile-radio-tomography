from ..core.Threadable import Threadable

class XBee_Sensor(Threadable):
    def __init__(self, thread_manager):
        super(XBee_Sensor, self).__init__("xbee_sensor", thread_manager)

    def enqueue(self, packet, to=None):
        raise NotImplementedError("Subclasses must implement enqueue(packet, to=None)")

    def _send(self):
        raise NotImplementedError("Subclasses must implement _send()")

    def _receive(self, packet):
        raise NotImplementedError("Subclasses must implement _receive(packet)")
