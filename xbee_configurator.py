import sys
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Configurator import XBee_Configurator

COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "end": "\033[0m"
}

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_configurator")
    arguments.check_help()

    for sensor_id in range(0, settings.get("number_of_sensors") + 1):
        if sensor_id == 0:
            raw_input("Connect the ground station XBee sensor and press Enter...")
        else:
            raw_input("Connect XBee sensor {} and press Enter...".format(sensor_id))

        parameters = {
            "ID": settings.get("pan_id"),
            "NI": str(sensor_id),
            "PM": 0,
            "PL": 0
        }
        xbee_configurator = XBee_Configurator(arguments)

        # Show the current parameters.
        for key in parameters.iterkeys():
            value = xbee_configurator.get(key)
            if value != None:
                print("{}[Sensor {}] {} is {}.{}".format(COLORS["green"], sensor_id, key, value, COLORS["end"]))
            else:
                print("{}[Sensor {}] {} is unknown.{}".format(COLORS["red"], sensor_id, key, COLORS["end"]))

        # Set the new parameters.
        for key, value in parameters.iteritems():
            if xbee_configurator.set(key, value):
                print("{}[Sensor {}] {} set to {}.{}".format(COLORS["green"], sensor_id, key, value, COLORS["end"]))
            else:
                print("{}[Sensor {}] {} not set to {}.{}".format(COLORS["red"], sensor_id, key, value, COLORS["end"]))

        # Write the changes to the sensor.
        if xbee_configurator.write():
            print("{}[Sensor {}] Changes written to sensor.{}".format(COLORS["green"], sensor_id, COLORS["end"]))
        else:
            print("{}[Sensor {}] Changes not written to sensor.{}".format(COLORS["red"], sensor_id, COLORS["end"]))

        del xbee_configurator

if __name__ == "__main__":
    main(sys.argv[1:])
