import struct
from ..settings import Settings
from XBee_Packet import XBee_Packet

class XBee_Custom_Packet(XBee_Packet):
    def __init__(self):
        """
        Initialize the custom XBee packet. In addition to a regular XBee
        packet, custom packets must adhere to a fixed specification. The
        specifications for all available packet types are listed in the
        settings JSON file.
        """

        super(XBee_Custom_Packet, self).__init__()
        settings = Settings("settings.json", "xbee_base")
        self.specifications = settings.get("specifications")

    def serialize(self):
        """
        Serialize a contents dictionary as a single byte-encoded string.
        After making sure that the dictionary adheres to the provided
        specification, we process the fields in the same order as in
        the specification.

        The specifications are part of a custom developed format for these
        byte-encoded strings. The first byte is always the specification
        identifier, which in the settings JSON can be found as the
        'value' key. The remaining bytes are added in order according to
        the specification. For instance, if the specification has two fields
        that are both doubles, then 16 additional bytes will be added.
        """

        # Verify that the specification has been provided.
        if "specification" not in self._contents:
            raise KeyError("No specification has been provided")

        specification_name = self._contents["specification"]

        # Verify that the provided specification exists.
        if specification_name not in self.specifications:
            raise KeyError("Unknown specification has been provided")

        specification = self.specifications[specification_name]
        self._contents.pop("specification")

        # Verify that all fields in the specification have been provided.
        # Skip fields with a value (usually identifier fields) as in that
        # case the provided value will be used.
        for field in specification:
            name = field["name"]
            if name not in self._contents and "value" not in field:
                raise KeyError("Field '{}' has not been provided.".format(name))

        # Pack the fields in the same order as in the specification. The
        # order is important as the same order is used to unpack.
        packed_message = ""
        for field in specification:
            if "value" in field:
                value = field["value"]
            else:
                value = self._contents[field["name"]]

            packed_message += struct.pack(field["format"], value)

        return packed_message

    def unserialize(self, contents):
        """
        Unserialize a given byte-encoded string as a contents dictionary.
        Essentially we reverse the serialization process by first unpacking
        the specification identifier byte. Using that we identify the
        used specification for the rest of the message. We unpack each
        field as provided in the specification in order. This is possible
        because the specification contains the number of bytes required
        per field, allowing us to jump through the byte-encoded string
        using an offset.
        """

        # Unpack the specification identifier.
        specification_id = struct.unpack_from("B", contents)[0]
        offset = struct.calcsize("B")

        # Fetch the specification belonging to the found identifier.
        specification = None
        specification_name = ""
        for name, fields in self.specifications.iteritems():
            if fields[0]["value"] == specification_id:
                specification = fields
                specification_name = name
                break

        if specification == None:
            raise ValueError("Invalid specification has been provided")

        # Loop through all fields in the specification that do not have
        # a fixed value (in order). Using the format of the field, we
        # can unpack the right part of the byte-encoded string. The offset
        # is used to continue from the last read part of the string.
        self._contents["specification"] = specification_name
        for field in specification:
            if "value" in field:
                continue

            name = field["name"]
            format = field["format"]
            self._contents[name] = struct.unpack_from(format, contents, offset)[0]
            offset += struct.calcsize(format)
