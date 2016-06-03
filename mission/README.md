# Mission classes

This module contains a number of mission classes that are based on the 
[DroneKit SDK](http://python.dronekit.io/). Some of these missions are based on 
the example scripts from the DroneKit core code. The latest versions and commit 
history of these scripts, as well as other examples, can be found in the master 
repository at https://github.com/dronekit/dronekit-python/tree/master/examples.

The example scripts from DroneKit are available under the
[Apache Licence 2.0](http://www.apache.org/licenses/LICENSE-2.0.html), which is 
compatible with the GNU General Public Licence version 3 in the sense that we 
can distribute it under the latter license. See the LICENSE file in the main 
directory for this license.

The missions direct a vehicle to move around in an environment and handle 
distance sensor measurements and waypoint traversal. They can make use of 
servos and other vehicle status to determine what to do, or create and follow 
an automated mission. Most missions work with all vehicle types, but some 
require specific setups.
