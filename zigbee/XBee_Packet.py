import json

class XBee_Packet(object):
    def __init__(self):
        """
        Initialize the packet with an empty contents key-value store.
        """

        self._contents = {}

    def set(self, key, value):
        """
        Set a key and value in the contents key-value store.
        """

        self._contents[key] = value

    def unset(self, key):
        """
        Unset a key in the contents key-value store.
        """

        if key in self._contents:
            self._contents.pop(key)

    def get(self, key):
        """
        Get the value of a key in the contents key-value store.
        """

        if key in self._contents:
            return self._contents[key]

        return None

    def serialize(self):
        """
        Convert the contents object to a JSON string.
        """

        return json.dumps(self._contents)

    def unserialize(self, contents):
        """
        Convert the JSON string to a contents object.
        """

        self._contents = json.loads(contents)
