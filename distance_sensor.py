import time
import RPi.GPIO as gpio

DELAY = 0.5 # seconds
SPEED_OF_SOUND = 34320 # cm/second

class Distance_Sensor(object):
    def __init__(self, trigger, echo):
        # Disable warnings about pins being in use
        gpio.setwarnings(False)

        # Use board numbering which corresponds to the
        # pin numbers on the P1 header of the board.
        gpio.setmode(gpio.BOARD)

        self.trigger = trigger
        self.echo = echo

        # Configure the input and output pins
        gpio.setup(self.trigger, gpio.OUT)
        gpio.setup(self.echo, gpio.IN)
        
        # Set trigger to false
        gpio.output(self.trigger, False)
        time.sleep(DELAY)

    def run(self):
        while True:
            # Trigger the sensor to start measuring
            gpio.output(self.trigger, True)
            time.sleep(0.00001)
            gpio.output(self.trigger, False)

            # Set the start time only when the sensor
            # is starting to send a signal
            start = time.time()
            while gpio.input(self.echo) == 0:
                start = time.time()

            # Move the end time when the signal has
            # not been returned yet.
            while gpio.input(self.echo) == 1:
                end = time.time()

            # Calculate the distance and divide by two
            # because the signal travels the distance
            # twice (back and forth).
            total = end - start
            distance = (total * SPEED_OF_SOUND) / 2
            print("Distance to object: {} cm".format(distance))

            time.sleep(DELAY)

def main():
    trigger = 13
    echo = 11

    distance_sensor = Distance_Sensor(trigger, echo)
    distance_sensor.run()

if __name__ == "__main__":
    main()
