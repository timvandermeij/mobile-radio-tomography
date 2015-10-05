from settings import Settings
from zigbee.XBee_Configurator import XBee_Configurator

def main():
    settings = Settings("settings.json", "xbee_configurator")

    for id in range(0, settings.get("number_of_sensors") + 1):
        if id == 0:
            raw_input("Connect the ground station XBee sensor and press Enter.")
        else:
            raw_input("Connect XBee sensor {} and press Enter...".format(id))

        xbee_configurator = XBee_Configurator(id, settings.get("source"), settings.get("baud_rate"))
        xbee_configurator.set("ID", settings.get("pan_id"))
        xbee_configurator.set("NI", str(id))
        xbee_configurator.write()
        xbee_configurator.get("ID")
        xbee_configurator.get("NI")
        del xbee_configurator

if __name__ == "__main__":
    main()
