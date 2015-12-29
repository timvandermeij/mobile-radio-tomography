[![Build status](https://travis-ci.org/timvandermeij/unmanned-vehicle-tomography.svg)](https://travis-ci.org/timvandermeij/unmanned-vehicle-tomography)

The unmanned vehicle tomography framework contains tools to perform radio tomographic
imaging using XBee chips mounted on unmanned vehicles such as rover cars or drones.
The goal of this work is to map an object in 3D using signal strength measurements.
This framework is the result of research projects performed by Tim van der Meij
(@timvandermeij) and Leon Helwerda (@lhelwerd) in collaboration with Leiden University
and CWI Amsterdam, both based in the Netherlands.

Prerequisites
=============

In order to use the toolchain you need to have the following software
installed on your system. The toolchain has been developed for Linux, but
can be made to work on Windows or any other operating system since all
prerequisites are also available for those systems, perhaps with slightly
different installation procedures.

* Git
* Python 2.7. Note that Python 3 cannot be used at this moment.
* `pip` for Python 2.7. `pip` is often not available on extremely old and bare
  systems. If it is also not delivered by a package manager, one can also
  [install it with get-pip.py](https://pip.pypa.io/en/latest/installing.html).
  Ensure that you have the correct version of `pip` with `pip --version` or use
  `pip2` instead.

  Use `pip install --user <package>` to install each of the following packages,
  sorted by purpose:
  * General packages:
    * matplotlib
    * NumPy
    * scipy
  * Physical sensor/communication interfaces:
    * pyserial (you may need to use `pip install --user "pyserial==2.7"`)
    * RPi.GPIO
    * xbee
  * Vehicle trajectory mission interfaces:
    * lxml
    * pexpect
    * pymavlink
    * mavproxy
    * droneapi
  * Environment simulation:
    * PyOpenGL
    * simpleparse
    * PyVRML97 (you may need to use `pip install --user "PyVRML97==2.3.0b1"`)
    * PyDispatcher
    * pyglet
  * Unit testing:
    * mock
* In order to use the map display of ArduPilot, make sure that OpenCV and 
  wxWidgets as well as their respective Python bindings are installed and 
  available. If not, the following directions might help you get it:
  * OpenCV: This is sometimes provided by the package manager. It can also be 
    installed from the [official download](http://opencv.org/downloads.html) 
    using the appropriate 
    [documentation](http://docs.opencv.org/2.4/doc/tutorials/introduction/table_of_content_introduction/table_of_content_introduction.html). 
    Note that for Linux, you must change the install prefix for `cmake` if you 
    do not have superuser rights. You can speed up the installation by passing 
    `-j4` to the `cmake` command.
  * wxWidgets: Again, if this is not provided by the package manager, see an 
    [explanation](http://wiki.wxpython.org/How%20to%20install%20wxPython) on 
    how to install from source. This requires wxGTK as well as the wxWidgets 
    library itself: these are combined within 
    a [download](http://www.wxwidgets.org/downloads/). You can install without 
    superuser rights using `./configure --with-gtk --prefix=$HOME/.local`.
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

    $ git clone https://github.com/timvandermeij/unmanned-vehicle-tomography.git
    $ cd unmanned-vehicle-tomography

Running the tools
=================

Now that we have a copy of the software, we can run the tools. Use `sudo` if
your user is not part of the `dialout` or `uucp` group.

XBee configurator
-----------------

The XBee configurator is used to quickly prepare all XBee sensors in the
network. Launch the configurator with `python2 xbee_configurator.py` to
get started. You might need to adjust the settings for the `xbee_configurator`
component in `settings.json`, for example to set the right port if the
default port is not correct (or use the command line options). After starting
the tool, the instructions for configuring each sensor are displayed on the
screen. The tool takes care of setting all required parameters.

Vehicle mission
---------------

The trajectory mission sets up an unmanned aerial vehicle (UAV) and directs it
to move and rotate within its environment. The script supports various mission
types and simulation modes. You can run it using the ArduPilot simulator with
the following command:

    $ sim_vehicle.sh -v ArduCopter --map
    [...wait until the simulator is set up, after "GPS lock at 0 meters"...]
    STABILIZE> script mission.scr

This starts the mission with default settings from `settings.json`. The
ArduPilot simulator provides an overhead map showing the copter's position.
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
important setting might be the mission class to use for calculating what
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

XBee sensor (physical)
----------------------

The physical XBee sensor code controls one XBee chip connected to the
device via USB. Such a device can either be a computer or a Raspberry
Pi. Start `screen` and run `python2 xbee_sensor_physical.py` to
activate the XBee chip mounted onto an XBee USB dongle. Each sensor
constantly receives packets (asynchronously), but sends packets according
to a fixed TDMA schedule as defined by the settings in `settings.json`.

To create the setup, first plug the ground station XBee chip into a USB
port of the ground station computer. Start the physical XBee sensor code
as mentioned above and observe that nothing is happening yet. Then, for
each other XBee chip in the network, power up the accompanying Raspberry
Pi, connect it to the ground station computer via an ethernet cable as 
described in the Raspberry Pi document, plug in the XBee USB dongle
and start the physical XBee sensor code as mentioned above. You should now
see packets arriving in the ground station's terminal. Note that once the
process is running, you can detach the screen and disconnect the ethernet
cable to have unconnected nodes that you can move around (assuming that
they are powered by a battery pack).

Distance sensor (physical)
--------------------------

We assume that you have setup a Raspberry Pi with Arch Linux ARM and
that you have connected the HC-SR04 sensor. This tool must run on the
Raspberry Pi. Start the tool with `python2 distance_sensor_physical.py`
to receive continuous measurements from the distance sensor. Change the pin
numbers for the trigger and echo pins in `settings.json` if you have used
different pin numbers when connecting the HC-SR04 sensor to the Raspberry Pi.

Running the unit tests
======================

The framework contains unit tests to ensure that all components behave the
way we expect them to behave and therefore to reduce the risk of introducing
regressions during development. The unit tests have to be executed from the
root folder using the following command:

    $ python2 -m unittest discover -s tests -p "*.py" -t ..

The result of running all unit tests should be "OK" in the terminal. This
command is executed automatically by Travis CI for each pull request or push
to a branch.

License
=======

The toolchain is licensed under a GPL v3 license. Refer to the `LICENSE`
file for more information.
