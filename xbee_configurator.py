from settings import Settings
from zigbee.XBee_Configurator import XBee_Configurator

COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "end": "\033[0m"
}

def report(id, message, color=None):
    if color == None:
        print("[Sensor {}] {}".format(id, message))
    else:
        print("{}[Sensor {}] {}{}".format(COLORS[color], id, message, COLORS["end"]))

def get(id, name, parameter, configurator):
    report(id, "Getting the {}...".format(name))
    value = configurator.get(parameter)
    if value != None:
        report(id, "Done getting the {}: {}'.".format(name, value), "green")
    else:
        report(id, "Failed getting the {}.".format(name), "red")

def set(id, name, parameter, value, configurator):
    report(id, "Setting the {} to '{}'...".format(name, value))
    success = configurator.set(parameter, value)
    if success:
        report(id, "Done setting the {} to '{}'.".format(name, value), "green")
    else:
        report(id, "Failed setting the {} to '{}'.".format(name, value), "red")

def write(id, configurator):
    report(id, "Writing queued changes...")
    success = configurator.write()
    if success:
        report(id, "Done writing queued changes.", "green")
    else:
        report(id, "Failed writing queued changes.", "red")

def main():
    settings = Settings("settings.json", "xbee_configurator")

    for id in range(0, settings.get("number_of_sensors") + 1):
        if id == 0:
            raw_input("Connect the ground station XBee sensor and press Enter.")
        else:
            raw_input("Connect XBee sensor {} and press Enter...".format(id))

        xbee_configurator = XBee_Configurator(id, settings.get("port"), settings.get("baud_rate"))

        set(id, "PAN ID", "ID", settings.get("pan_id"), xbee_configurator)
        set(id, "node ID", "NI", str(id), xbee_configurator)
        write(id, xbee_configurator)
        get(id, "PAN ID", "ID", xbee_configurator)
        get(id, "node ID", "NI", xbee_configurator)

        del xbee_configurator

if __name__ == "__main__":
    main()
