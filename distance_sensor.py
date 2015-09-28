import time
from __init__ import __package__
from settings import Settings
from distance.Distance_Sensor_Physical import Distance_Sensor_Physical

def main():
    distance_sensor = Distance_Sensor_Physical()
    settings = Settings("settings.json", "distance_sensor_physical")

    while True:
        print("Measured distance: {} m".format(distance_sensor.get_distance()))
        time.sleep(settings.get("interval_delay"))

if __name__ == "__main__":
    main()
