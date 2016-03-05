import time
from __init__ import __package__
from settings import Settings
from core.Thread_Manager import Thread_Manager
from control.Infrared_Sensor import Infrared_Sensor

def start_callback():
    print("Start button pressed")

def stop_callback():
    print("Stop button pressed")

def main():
    thread_manager = Thread_Manager()

    try:
        settings = Settings("settings.json", "infrared_sensor")
        infrared_sensor = Infrared_Sensor(settings, thread_manager)
        infrared_sensor.register("start", start_callback)
        infrared_sensor.register("stop", stop_callback)
        infrared_sensor.activate()

        while True:
            time.sleep(1)
    except:
        thread_manager.destroy()

if __name__ == "__main__":
    main()
