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
prerequisites are also available for those systems, perhaps with slightly
different installation procedures.

* Git
* Python 2.7. Note that Python 3 cannot be used at this moment.
* `pip` for Python 2.7. `pip` is often already available extremely old and bare
  systems. If it is also not delivered by a package manager, one can also
  [install with get-pip.py](https://pip.pypa.io/en/latest/installing.html).
  Ensure you have the correct version of `pip` with `pip --version`, or use
  `pip2` instead.

  Use `pip install --user <package>` to install each of the following packages,
  sorted by purpose:
  * General packages:
    * matplotlib
    * NumPy
    * scipy
  * Physical sensor/communication interfaces:
    * pyserial
    * RPi.GPIO
    * xbee
  * Vehicle trajectory mission interfaces:
    * lxml
    * pexpect
    * pymavlink
    * mavproxy
    * droneapi
  * Environment simulation:
    * OpenGLContext
    * PyVRML97
    * PyDispatcher
    * pyglet
  * Unit testing:
    * mock
* ArduPilot for vehicle simulation. Download the latest code using:

        $ git clone https://github.com/diydrones/ardupilot.git

  Then, add the following line to your `~/.bashrc`:

      export PATH=$PATH:$HOME/ardupilot/Tools/autotest

  Finally, create a file `~/.mavinit.src` with the following line:

      module load droneapi.module.api

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

Vehicle mission
---------------

The trajectory mission sets up an unmanned aerial vehicle (UAV) and directs it
to move and rotate within its environment. The script supports various mission
types and simulation modes. You can run it using the ArduPilot simulator using
the following commands:

    $ sim vehicle.sh -v ArduCopter --map
    [...wait until the simulator is set up, after "GPS lock at 0 meters"...]
    STABILIZE> script mission.scr

This starts up the mission with default settings from `settings.json`.
The ArduPilot simulator provides an overhead map showing the copter's position.
The mission monitor has a map in memory that shows objects in the environment
during simulation as well as detected points from a distance sensor. It also
provides a 3D viewer of the simulated objects.

You can also start the mission monitor without ArduPilot simulation using
`python2 mission_basic.py`. In this case, the vehicle is simulated on our own,
and no overhead map is provided other than the memory map. The command allows
changing settings from their defaults using arguments. You can provide a VRML
scene file to retrieve simulated objects from using the `--scenefile` option,
change the geometry from a spherical coordinate system (`Geometry_Spherical`)
to a flat meter-based coordinate system using `--geometry-class Geometry`, or
set sensor positioning angles, for example `--sensors 0 90 -90`. Many other 
options are available for simulating various missions and sensor setups, and
the command `python2 mission_basic.py --help` provides a list of them. The most
important setting might be the Mission class to use for calculating what
trajectory to take. You can choose one of the classes in `trajectory/Mission.py`
using `--mission-class <Mission_Name>`.

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
