import time
from __init__ import __package__
from settings import Settings
from location.Line_Follower import Line_Follower_Direction
from location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

def callback():
    pass

def main():
    location = (0, 0)
    direction = Line_Follower_Direction.UP
    settings = Settings("settings.json", "line_follower_raspberry_pi")

    line_follower = Line_Follower_Raspberry_Pi(location, direction, callback, settings)

    while True:
        line_follower.activate()
        print(line_follower.read())
        line_follower.deactivate()
        time.sleep(1)

if __name__ == "__main__":
    main()
