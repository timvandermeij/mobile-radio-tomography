[![Build status](https://travis-ci.org/timvandermeij/drone-tomography.svg)](https://travis-ci.org/timvandermeij/drone-tomography)

The drone tomography toolchain contains tools to perform radio tomography
using XBee chips mounted on drones. The goal of this work is to be able
to map an object in 3D using collected radio tomography data. This work is
the result of a research project performed by Tim van der Meij (@timvandermeij)
and Leon Helwerda (@lhelwerd) in collaboration with Leiden University and
CWI Amsterdam, both based in the Netherlands.

Prerequisites
=============

In order to use the toolchain you need to have the following software
installed on your system. The toolchain has been developed for Linux, but
can be made to work on Windows or any other operating system since all
prerequisites are also available for those systems.

* Git
* Python 2.7
* pip for Python 2.7 with the following packages:
    * pyserial
    * matplotlib
    * NumPy
    * RPi.GPIO
    * mock
    * xbee

For all commands in this file, replace `python2` with `python` if your
operating system does not need to distinguish between Python 2 and Python 3.

Cloning the repository
======================

The first step is to clone the repository to obtain a local copy of the 
code. Open a terminal and run the following commands.

    $ git clone https://github.com/timvandermeij/drone-tomography.git
    $ cd drone-tomography

Running the tools
=================

Now that we have a copy of the software, we can run the tools.

XBee sensor (simulator)
-----------------------

The XBee sensor simulator is used to simulate the behavior of an XBee
sensor network. This is especially useful for determining communication
schemes for the sensors. Start the tool on a laptop or desktop computer
with `python2 xbee_sensor_simulator.py` in a terminal to get both output
in the terminal as well as open a viewer that visualizes the communication
between the sensors in the network. Settings for the simulation, such as
the number of sensors in the network, can be altered in the `settings.json`
file.

Distance sensor (physical)
--------------------------

We assume that you have setup a Raspberry Pi with Arch Linux ARM and
that you have connected the HC-SR04 sensor. This tool must run on the
Raspberry Pi. Start the tool with `sudo python2 distance_sensor_physical.py`
to receive continuous measurements from the distance sensor. Change the pin
numbers for the trigger and echo pins in `settings.json` if you have used
different pin numbers when connecting the HC-SR04 sensor to the Raspberry Pi.

XBee configurator
-----------------

The XBee configurator is used to quickly prepare all XBee chips in the
network. Start the configurator with `sudo python2 xbee_configurator.py` to
get started. You might need to adjust the settings for the `xbee_configurator`
component in `settings.json`, for example to set the right port if the
default port is not correct. After starting the tool, the instructions for
configuring each sensor are displayed on the screen. The tool takes care of
setting the PAN ID and the node ID for each sensor.

Running the unit tests
======================

The drone tomography toolchain contains unit tests to ensure that all
components behave the way we expect them to behave and therefore to reduce
the risk of introducing regressions during development. The unit tests
have to be executed from the root folder using the following command:

    $ python2 -m unittest discover -s tests -p "*.py" -t ..

The result of running all unit tests should be "OK" in the terminal.

License
=======

The toolchain is licensed under a GPL v3 license. Refer to the `LICENSE`
file for more information.
