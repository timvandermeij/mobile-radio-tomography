import struct
from ..settings import Settings
from XBee_Packet import XBee_Packet

class XBee_Custom_Packet(XBee_Packet):
    def __init__(self):
        super(XBee_Custom_Packet, self).__init__()
        settings = Settings("settings.json", "xbee_base")
        self.specifications = settings.get("specifications")

    def serialize(self):
        if "specification" not in self._contents:
            raise KeyError("No specification has been provided")

        specification_name = self._contents["specification"]

        if specification_name not in self.specifications:
            raise KeyError("Unknown specification has been provided")

        specification = self.specifications[specification_name]
        self._contents.pop("specification")

        # Verify if all fields in the specification have been provided.
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
        specification_id = struct.unpack_from("B", contents)[0]
        offset = struct.calcsize("B")

        specification = None
        specification_name = ""
        for name, fields in self.specifications.iteritems():
            if fields[0]["value"] == specification_id:
                specification = fields
                specification_name = name
                break

        if specification == None:
            raise ValueError("Invalid specification has been provided")

        self._contents["specification"] = specification_name
        for field in specification:
            if "value" in field:
                continue

            name = field["name"]
            format = field["format"]
            self._contents[name] = struct.unpack_from(format, contents, offset)[0]
            offset += struct.calcsize(format)
