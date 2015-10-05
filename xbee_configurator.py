from zigbee.XBee_Configurator import XBee_Configurator

def main():
    id = 4
    xbee_configurator = XBee_Configurator(id, "/dev/ttyUSB1", 9600)
    xbee_configurator.set("ID", 5678)
    xbee_configurator.set("NI", str(id))
    xbee_configurator.write()
    xbee_configurator.get("ID")
    xbee_configurator.get("NI")
    del xbee_configurator

if __name__ == "__main__":
    main()
