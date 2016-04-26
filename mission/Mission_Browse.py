from Mission_Guided import Mission_Guided

class Mission_Browse(Mission_Guided):
    """
    Mission that stays at a fixed location and scans its surroundings.
    """

    def setup(self):
        super(Mission_Browse, self).setup()
        self.yaw = 0
        self.yaw_angle_step = self.settings.get("yaw_step")

    def step(self):
        # We stand still and change the angle to look around.
        self.send_global_velocity(0,0,0)
        self.set_sensor_yaw(self.yaw, relative=False, direction=1)

        # When we're standing still, we rotate the vehicle to measure distances 
        # to objects.
        self.yaw = (self.yaw + self.yaw_angle_step) % 360
