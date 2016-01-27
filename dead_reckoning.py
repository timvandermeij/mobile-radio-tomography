import random as rand
import time
from __init__ import __package__
from location.Dead_Reckoning_Map import Dead_Reckoning_Map

def main():
    dead_reckoning_map = Dead_Reckoning_Map()

    dead_reckoning_map.set(5, 90)
    dead_reckoning_map.plot()
    dead_reckoning_map.set(5, 180)
    dead_reckoning_map.plot()
    for i in range(0, 360, 20):
        dead_reckoning_map.set(0.5, 90 + i)
        dead_reckoning_map.plot()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
