import time
from __init__ import __package__
from distance import Distance_Sensor_Physical

def main():
    distance_sensor = Distance_Sensor_Physical()

    while True:
        print("Measured distance: {} m".format(distance_sensor.get_distance()))
        time.sleep(settigs.get("interval_delay"))

if __name__ == "__main__":
    main()
