from Environment import Environment
from ..distance.Distance_Sensor_Physical import Distance_Sensor_Physical

class Environment_Physical(Environment):
    _sensor_class = Distance_Sensor_Physical
