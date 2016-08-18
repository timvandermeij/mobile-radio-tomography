import random
import sys
import time
import traceback
from __init__ import __package__
from core.Import_Manager import Import_Manager
from core.Thread_Manager import Thread_Manager
from core.USB_Manager import USB_Manager
from settings import Arguments

def get_location():
    return (random.randint(0, 5), random.randint(0, 5)), random.randint(0, 5)

def receive_packet(packet):
    print("Received packet: {}".format(packet.get_all()))

def location_valid(other_valid=None, other_id=None, other_index=None):
    return True

def main(argv):
    import_manager = Import_Manager()
    thread_manager = Thread_Manager()
    usb_manager = USB_Manager()

    usb_manager.index()

    arguments = Arguments("settings.json", argv, positionals=[{
        "name": "rf_sensor_class",
        "help": "Sensor class to use for the RF sensor",
        "type": "class",
        "module": "zigbee.RF_Sensor",
        "required": True
    }])

    rf_sensor_class = arguments.get_positional_value("rf_sensor_class")
    rf_sensor_type = import_manager.load_class(rf_sensor_class,
                                               relative_module="zigbee")
    rf_sensor = rf_sensor_type(arguments, thread_manager, get_location,
                               receive_packet, location_valid, usb_manager=usb_manager)

    arguments.check_help()

    try:
        rf_sensor.activate()

        print("RF sensor has joined the network.")
        while True:
            if rf_sensor.id == 0:
                # The ground station does not need to start in order to receive 
                # measurements, so do not bother giving this possibility.
                time.sleep(1)
            else:
                # Wait for the user to determine when to perform measurements 
                # and when to stop. Add a newline so that the messages do not 
                # mess up other output.
                raw_input("Press Enter to start measurements...\n")
                rf_sensor.start()

                raw_input("Press Enter to stop measurements...\n")
                rf_sensor.stop()
    except:
        traceback.print_exc()
        thread_manager.destroy()
        usb_manager.clear()

if __name__ == "__main__":
    main(sys.argv[1:])
