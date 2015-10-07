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

    sender = 0
    while True:
        try:
            sensors[sender]._send()
            sender = not sender

            time.sleep(settings.get("loop_delay"))
        except IOError:
            break
        except KeyboardInterrupt:
            break

    for sensor in sensors:
        del sensor

if __name__ == "__main__":
    main(sys.argv[1:])
