# Arduino programs

This directory contains programs that can be compiled and transferred to an 
Arduino board. Such a program can then make it possible to interface with other 
peripherals, such as a robot vehicle or serial connections with other devices.

The compilation and transfer steps require the use of the [Arduino 
IDE](https://www.arduino.cc/en/Main/Software) which can be easily downloaded 
and extracted/installed on various platforms. Additionally, the Arduino must be 
powered and connected to the machine running the IDE during these steps. You 
can use a USB (to type B) cable or TTL interface. Some (parts) of the programs 
are based on the [Zumo library](https://github.com/pololu/zumo-shield), which 
also needs to be downloaded. Put all the directories from the Zumo library in 
the `libraries` directory of the Arduino IDE sketchbook, except for the 
examples (you can put those in the sketchbook itself, if you want). After this, 
open the programs from this directory in the IDE so that they are moved over to 
the sketchbook as well.
