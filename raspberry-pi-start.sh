#!/bin/sh
cd /home/alarm/mobile-radio-tomography
python2 mission_basic.py --vehicle-class Robot_Vehicle_Arduino --mission-class Mission_Infrared --geometry-class Geometry --servo-pins --distance-sensors --no-plot --no-viewer --speed 0.2 --step-delay 0.25 > logs/output.log 2> logs/error.log
