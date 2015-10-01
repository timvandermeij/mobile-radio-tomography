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
    * matplotlib
    * NumPy
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
with `python2 xbee_sensor_simulator.py` in a terminal to get both output
in the terminal as well as open a viewer that visualizes the communication
between the sensors in the network. One can alter settings for the
simulation, such as the number of sensors in the network, in the
`settings.json` file.

Distance sensor
---------------

We assume that you have setup a Raspberry Pi with Arch Linux ARM and
that you have connected the HC-SR04 sensor. This tool must run on the
Raspberry Pi. Start the tool with `sudo python2 distance_sensor.py` to
receive continuous measurements from the distance sensor. Change the pin
numbers for the trigger and echo pins in `settings.json` if you have used
different pin numbers when connecting the HC-SR04 sensor to the Raspberry
Pi.

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
