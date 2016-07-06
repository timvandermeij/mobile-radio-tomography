#!/bin/sh
cd /home/alarm/mobile-radio-tomography
stdbuf -oL -eL python2 mission_basic.py --vehicle-class Robot_Vehicle_Arduino_Full --geometry-class Geometry_Grid --servo-pins --distance-sensors --no-plot --no-viewer --speed 0.3 --rf-sensor-class RF_Sensor_Physical_Texas_Instruments --synchronize --closeness 0 > logs/output$$.log 2> logs/error$$.log
