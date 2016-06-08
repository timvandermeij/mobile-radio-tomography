#!/bin/sh
cd /home/alarm/mobile-radio-tomography
stdbuf -oL -eL python2 mission_basic.py --vehicle-class Robot_Vehicle_Arduino_Full --mission-class Mission_XBee --geometry-class Geometry --servo-pins --distance-sensors --no-plot --no-viewer --speed 0.3 --xbee-type XBee_Sensor_Physical --synchronize --closeness 0 > logs/output$$.log 2> logs/error$$.log
