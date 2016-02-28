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

if __name__ == "__main__":
    main()
