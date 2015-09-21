import time
import RPi.GPIO as gpio

TRIGGER_PIN = 13
ECHO_PIN = 11
TRIGGER_DELAY = 0.00001 # seconds
INTERVAL_DELAY = 0.5 # seconds
SPEED_OF_SOUND = 34320 # cm/second

class Distance_Sensor(object):
    def __init__(self):
        # Disable warnings about pins being in use
        gpio.setwarnings(False)

        # Use board numbering which corresponds to the
        # pin numbers on the P1 header of the board.
        gpio.setmode(gpio.BOARD)

        # Configure the input and output pins
        gpio.setup(TRIGGER_PIN, gpio.OUT)
        gpio.setup(ECHO_PIN, gpio.IN)
        
        # Set trigger to false
        gpio.output(TRIGGER_PIN, False)
        time.sleep(INTERVAL_DELAY)

    def run(self):
        while True:
            # Trigger the sensor to start measuring
            gpio.output(TRIGGER_PIN, True)
            time.sleep(TRIGGER_DELAY)
            gpio.output(TRIGGER_PIN, False)

            # Set the start time only when the sensor
            # is starting to send a signal
            start = time.time()
            while gpio.input(ECHO_PIN) == 0:
                start = time.time()

            # Move the end time when the signal has
            # not been returned yet.
            while gpio.input(ECHO_PIN) == 1:
                end = time.time()

            # Calculate the distance and divide by two
            # because the signal travels the distance
            # twice (back and forth).
            total = end - start
            distance = (total * SPEED_OF_SOUND) / 2
            print("Distance to object: {} cm".format(distance))

            time.sleep(INTERVAL_DELAY)

def main():
    distance_sensor = Distance_Sensor()
    distance_sensor.run()

if __name__ == "__main__":
    main()
