The drone tomography toolchain contains tools to perform radio tomography
using XBee chips mounted on drones. The goal of this work is to be able
to map an object in 3D using collected radio tomography data. This work is
the result of a research project performed by Tim van der Meij (@timvandermeij)
and Leon Helwerda (@lhelwerd) in collaboration with Leiden University and
CWI Amsterdam, both based in the Netherlands.

Prerequisites
=============

In order to use the toolchain you need to have the following software
installed on your system. The software has been developed for Linux, but
can be made to work on Windows or any other operating system since all
prerequisites are also available for those systems. The version numbers
mentioned below have been verified, but other versions are also likely
to work.

* Git 2.5.3
* Python 2.7.10
* pip 7.1.2 with the following packages:
    * RPi.GPIO

For all commands in this file, replace `python2` with `python` if your
operating system does not need to distinguish between Python 2 and Python 3.

Cloning the repository
======================

The first step is to clone the repository to obtian a local copy of the 
code. Open a terminal and run the following commands.

    $ git clone https://github.com/timvandermeij/drone-tomography.git
    $ cd drone-tomography

Running the tools
=================

Now that we have a copy of the software, we can run the tools.

XBee sensor simulator
---------------------

The XBee sensor simulator is used to simulate the behavior of an XBee
sensor network. This is especially useful for determining communication
schemes for the sensors. Start the tool on a laptop or desktop computer
with `python2 xbee_sensor_simulator.py -i 1` in one terminal and with
`python2 xbee_sensor_simulator.py -i 2` in another terminal to simulate
the communication between sensors 1 and 2. You can add more sensors to the
network by opening more terminals and using unique sensor IDs for the `-i`
flag.

Distance sensor
---------------

We assume that you have setup a Raspberry Pi with Arch Linux ARM and
that you have connected the HC-SR04 sensor. This tool must run on the
Raspberry Pi. Start the tool with `sudo python2 distance_sensor.py` to
receive continuous measurements from the distance sensor.

License
=======

The toolchain is licensed under a GPL v3 license. Refer to the `LICENSE`
file for more information.
