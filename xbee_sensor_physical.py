import sys
import time
from __init__ import __package__
from settings import Arguments
from zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("xbee_sensor_physical")

    sensors = []
    for sensor_id in range(1, settings.get("number_of_sensors") + 1):
        sensor = XBee_Sensor_Physical(sensor_id, arguments)
        sensors.append(sensor)

    arguments.check_help()

    sender = 1
    while True:
        try:
            sensors[sender - 1]._send()
            if sender == 1:
                sender = 2
            else:
                sender = 1

            time.sleep(settings.get("loop_delay"))
        except IOError:
            break
        except KeyboardInterrupt:
            break

    for sensor in sensors:
        del sensor

if __name__ == "__main__":
    main(sys.argv[1:])
