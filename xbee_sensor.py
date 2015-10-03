import sys
import time
from settings import Settings
from __init__ import __package__
from xbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator
from xbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from xbee.XBee_Viewer import XBee_Viewer

def main(argv):
    settings = Settings("settings.json", "xbee_sensor_simulator")

    viewer = XBee_Viewer(settings)
    viewer.draw_points()

    sensors = []
    for sensor_id in range(settings.get("number_of_sensors") + 1):
        scheduler = XBee_TDMA_Scheduler(settings, sensor_id)
        sensor = XBee_Sensor_Simulator(sensor_id, settings, scheduler, viewer)
        sensors.append(sensor)

    while True:
        for sensor in sensors:
            sensor.activate()
        
        time.sleep(settings.get("loop_delay"))

if __name__ == "__main__":
    main(sys.argv[1:])
