import time
import dronekit
from dronekit import VehicleMode
from pymavlink import mavutil
from Vehicle import Vehicle
from MAVLink_Vehicle import MAVLink_Vehicle
from ..settings.Arguments import Arguments

class Dronekit_Vehicle(dronekit.Vehicle, MAVLink_Vehicle):
    """
    A vehicle that connects to a backend using MAVLink and the Dronekit library.
    """

    def __new__(cls, arguments, *a):
        if isinstance(arguments, Arguments):
            settings = arguments.get_settings("vehicle_dronekit")
            connect = settings.get("connect")
            baud_rate = settings.get("mavlink_baud_rate")
            vehicle = dronekit.connect(connect, baud=baud_rate, vehicle_class=cls)
            return vehicle
        else:
            return super(Dronekit_Vehicle, cls).__new__(cls, arguments, *a)

    def __init__(self, handler, geometry=None, import_manager=None,
                 thread_manager=None, usb_manager=None):
        if isinstance(handler, Arguments):
            # Call the constructor of Threadable, which is the superclass of 
            # the Vehicle base class, to make ourselves managed by the thread 
            # manager.
            # pylint: disable=bad-super-call
            super(Vehicle, self).__init__("dronekit_vehicle", thread_manager)
            self.settings = handler.get_settings("vehicle_dronekit")
            self._geometry = geometry
            # Because the dronekit Vehicle starts a MAVLink connection thread 
            # immediately, register ourselves in the thread manager now.
            super(Dronekit_Vehicle, self).activate()
        else:
            super(Dronekit_Vehicle, self).__init__(handler)

            self.add_message_listener('*', self.get_packet)

            # Create home location listener
            @self.on_message(['WAYPOINT', 'MISSION_ITEM'])
            def listener(self, name, msg):
                if not self._wp_loaded and msg.seq == 0:
                    self.notify_attribute_listeners('home_location', self.home_location)

        self.is_rover = False
        self.wait = False
        self._speed = 0.0

    def deactivate(self):
        super(Dronekit_Vehicle, self).deactivate()
        # Close the MAVLink connection thread.
        self.close()

    def setup(self):
        # Whether to use GPS and thus also wait for a GPS fix before arming.
        self.use_gps = self.settings.get("gps")

        # Wait until location has been filled
        if self.use_gps:
            self.wait = True
            self.add_attribute_listener('location.global_relative_frame', self._listen)

            while self.wait:
                time.sleep(1.0)
                print('Waiting for location update...')

        self.parameters['ARMING_CHECK'] = 0

    def _listen(self, vehicle, attr_name, value):
        vehicle.remove_attribute_listener('location.global_relative_frame', self._listen)
        self.wait = False

    def get_packet(self, vehicle, msg_type, msg):
        if msg_type == "HEARTBEAT":
            if msg.type == mavutil.mavlink.MAV_TYPE_GROUND_ROVER:
                self.is_rover = True
        elif msg_type == "SERVO_OUTPUT_RAW":
            servo_pwms = {}
            for field in msg.get_fieldnames():
                if field.startswith("servo") and field.endswith("raw"):
                    key = int(field[len("servo"):-len("raw")-1])
                    servo_pwms[key] = getattr(msg, field)

            self.notify_attribute_listeners('servos', servo_pwms)

    def check_arming(self):
        # Don't let the user try to fly autopilot is booting
        while self.mode.name == "INITIALISING":
            print("Waiting for vehicle to initialise...")
            time.sleep(1)
        while self.use_gps and self.gps_0.fix_type < 2:
            print("Waiting for GPS...: {}".format(self.gps_0.fix_type))
            time.sleep(1)

        if self.is_rover:
            # Rover is already armed and does not need to take off.
            return True

        # Copter should arm in GUIDED mode
        self.mode = dronekit.VehicleMode("GUIDED")

        return True

    def pause(self):
        if self.is_rover:
            self.mode = dronekit.VehicleMode("HOLD")
        else:
            self.mode = dronekit.VehicleMode("LOITER")

        self.flush()

    def add_takeoff(self, altitude):
        if self.is_rover:
            return False

        return super(Dronekit_Vehicle, self).add_takeoff(altitude)

    def simple_takeoff(self, altitude=None):
        if self.is_rover:
            return False

        super(Dronekit_Vehicle, self).simple_takeoff(altitude)
        return True

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        msg = self.message_factory.command_long_encode(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # command
            0, # confirmation
            0, # param 1
            speed, # speed in meters/second
            100, # throttle as a percentage (Rover only)
            0, 0, 0, 0 # param 4 - 7
        )

        # Send command to vehicle
        self.send_mavlink(msg)
        self._speed = speed

    velocity = dronekit.Vehicle.velocity

    @velocity.setter
    def velocity(self, velocity):
        msg = self.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, # frame
            0b0000111111000111, # type_mask (only speeds enabled)
            0, # lat_int - X Position in WGS84 frame in 1e7 * meters
            0, # lon_int - Y Position in WGS84 frame in 1e7 * meters
            0, # alt - Altitude in meters in AMSL altitude(not WGS84 if absolute or relative)
            velocity[0], # X velocity in NED frame in m/s
            velocity[1], # Y velocity in NED frame in m/s
            velocity[2], # Z velocity in NED frame in m/s
            0, 0, 0,     # afx, afy, afz acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)        # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)

        # Send command to vehicle
        self.send_mavlink(msg)

    def set_yaw(self, heading, relative=False, direction=1):
        if self.is_rover:
            if self.mode.name != "STEERING":
                self.mode = VehicleMode("STEERING")
                self.flush()
            return

        if relative:
            is_relative = 1 # yaw relative to direction of travel
        else:
            is_relative = 0 # yaw is an absolute angle

        # Create the CONDITION_YAW command using command_long_encode()
        msg = self.message_factory.command_long_encode(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_CONDITION_YAW, # command
            0, # confirmation
            heading,     # param 1, yaw in degrees
            1,           # param 2, yaw speed deg/s (ignored)
            direction,   # param 3, direction -1 ccw, 1 cw
            is_relative, # param 4, relative offset 1, absolute angle 0
            0, 0, 0      # param 5 ~ 7 not used
        )

        # Send command to vehicle
        self.send_mavlink(msg)

    def set_servo(self, servo, pwm):
        pin = servo.get_pin()

        # Create the DO_SET_SERVO command using command_long_encode()
        msg = self.message_factory.command_long_encode(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO, # command
            0, # confirmation
            pin,          # param 1, servo pin number
            pwm,          # param 2, PWM value
            0, 0, 0, 0, 0 # param 3 ~ 7 not used
        )

        # Send command to vehicle
        self.send_mavlink(msg)

    @property
    def use_simulation(self):
        return self.settings.get("vehicle_simulation")

    home_location = dronekit.Vehicle.home_location

    @home_location.setter
    def home_location(self, pos):
        home_location = self._make_global_location(pos)
        dronekit.Vehicle.home_location.__set__(self, home_location)
        self.notify_attribute_listeners('home_location', home_location)
