import time
from __init__ import __package__
from settings import Settings
from control.Infrared_Sensor import Infrared_Sensor

def start_callback():
    print("Start button pressed")

def stop_callback():
    print("Stop button pressed")

def main():
    settings = Settings("settings.json", "infrared_sensor")
    infrared_sensor = Infrared_Sensor(settings)
    infrared_sensor.register("start", start_callback)
    infrared_sensor.register("stop", stop_callback)
    infrared_sensor.activate()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            infrared_sensor.deactivate()

if __name__ == "__main__":
    main()
