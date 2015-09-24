import time
import RPi.GPIO as gpio
from settings.Settings import Settings

class Distance_Sensor(object):
    def __init__(self, settings):
        self.settings = settings

        # Disable warnings about pins being in use
        gpio.setwarnings(False)

        # Use board numbering which corresponds to the
        # pin numbers on the P1 header of the board.
        gpio.setmode(gpio.BOARD)

        # Configure the input and output pins
        gpio.setup(self.settings.get("trigger_pin"), gpio.OUT)
        gpio.setup(self.settings.get("echo_pin"), gpio.IN)
        
        # Set trigger to false
        gpio.output(self.settings.get("trigger_pin"), False)
        time.sleep(self.settings.get("interval_delay"))

    def run(self):
        while True:
            # Trigger the sensor to start measuring
            gpio.output(self.settings.get("trigger_pin"), True)
            time.sleep(self.settings.get("trigger_delay"))
            gpio.output(self.settings.get("trigger_pin"), False)

            # Set the start time only when the sensor
            # is starting to send a signal
            start = time.time()
            while gpio.input(self.settings.get("echo_pin")) == 0:
                start = time.time()

            # Move the end time when the signal has
            # not been returned yet.
            while gpio.input(self.settings.get("echo_pin")) == 1:
                end = time.time()

            # Calculate the distance and divide by two
            # because the signal travels the distance
            # twice (back and forth).
            total = end - start
            distance = (total * self.settings.get("speed_of_sound")) / 2
            print("Distance to object: {} cm".format(distance))

            time.sleep(self.settings.get("interval_delay"))

def main():
    settings = Settings("settings.json", "distance_sensor")

    distance_sensor = Distance_Sensor(settings)
    distance_sensor.run()

if __name__ == "__main__":
    main()
