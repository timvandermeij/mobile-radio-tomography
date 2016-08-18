import time
from ..zigbee.Packet import Packet
from ..zigbee.TDMA_Scheduler import TDMA_Scheduler
from ..settings import Arguments
from settings import SettingsTestCase

class TestZigBeeTDMAScheduler(SettingsTestCase):
    def setUp(self):
        self.id = 2

        self.arguments = Arguments("settings.json", [
            "--number-of-sensors", "8", "--sweep-delay", "0.3"
        ])
        self.settings = self.arguments.get_settings("zigbee_tdma_scheduler")

        self.scheduler = TDMA_Scheduler(self.id, self.arguments)

        self.number_of_sensors = self.settings.get("number_of_sensors")
        self.sweep_delay = self.settings.get("sweep_delay")
        self.slot_time = float(self.sweep_delay) / self.number_of_sensors
        self.time_delta = 1e-5

    def test_initialization(self):
        # Verify that only `Arguments` objects can be used to initialize.
        TDMA_Scheduler(self.id, self.arguments)
        with self.assertRaises(TypeError):
            TDMA_Scheduler(self.id, self.settings)
        with self.assertRaises(TypeError):
            TDMA_Scheduler(self.id, None)

        # Member variables must be initialized properly.
        self.assertEqual(self.scheduler._number_of_sensors, self.number_of_sensors)
        self.assertEqual(self.scheduler._sweep_delay, self.sweep_delay)

        self.assertEqual(self.scheduler._id, self.id)
        self.assertEqual(self.scheduler._timestamp, 0)
        self.assertEqual(self.scheduler._slot_time, self.slot_time)

    def test_id(self):
        # It must be possible to set and get the ID of the sensor.
        self.scheduler.id = 1
        self.assertEqual(self.scheduler.id, 1)

    def test_timestamp(self):
        # It must be possible to get and set the timestamp for sending packets.
        self.assertEqual(self.scheduler.timestamp, 0)

        self.scheduler.timestamp = 12345678.90
        self.assertEqual(self.scheduler.timestamp, 12345678.90)

    def test_update(self):
        # The first time the method is called, the timestamp is based on the
        # current time `c`. If the total sweep takes `t` seconds, then the
        # timestamp is calculated as `c + (i / n) * t`, where `i` is the ID of
        # the sensor and `n` is the total number of sensors in the network.
        # This assures that each sensor gets an equally large time slot.
        self.scheduler.update()

        expected = time.time() + ((float(self.id) / self.number_of_sensors) *
                                  self.sweep_delay)
        self.assertAlmostEqual(self.scheduler.timestamp, expected,
                               delta=self.time_delta)

        # Any subsequent calls to the method should just increase the timestamp
        # (which might have been updated in the meantime by the `synchronize`
        # method) with the sweep delay to move to the next sweep.
        self.scheduler.update()

        expected += self.sweep_delay
        self.assertAlmostEqual(self.scheduler.timestamp, expected,
                               delta=self.time_delta)

    def test_synchronize(self):
        # If the received packet is from a sensor with a lower ID than the
        # current sensor, then the timestamp for the current sensor must be
        # calculated as the timestamp in the received packet plus the number
        # of slots inbetween them. For example, if sensor 2 receives a packet
        # from sensor 1, then sensor 2 must start sending right after sensor 1,
        # i.e., the timestamp for sensor 2 is the timestamp of sensor 1 plus the
        # time required for one slot.
        packet = Packet()
        packet.set("specification", "rssi_broadcast")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        packet.set("valid", True)
        packet.set("waypoint_index", 1)
        packet.set("sensor_id", 1)
        packet.set("timestamp", time.time())

        self.scheduler.synchronize(packet)

        expected = packet.get("timestamp") + ((self.id - packet.get("sensor_id")) * self.slot_time)
        self.assertAlmostEqual(self.scheduler.timestamp, expected,
                               delta=self.time_delta)

        # If the received packet is from a sensor with a higher ID than the
        # current sensor, then the next timestamp for the current sensor must
        # be calculated as the timestamp in the received packet plus the number
        # of slots required to complete the current sweep plus the number of slots
        # required before the current sensor is allowed to start transmitting.
        # For example, if sensor 2 receives a packet from sensor 6 and the total
        # number of slots is 8, then 8 - 6 + 1 = 3 slots are required to complete
        # the current sweep (as we need a full slot for sensors 6, 7 and 8).
        # We then need to add 2 - 1 = 1 slot for sensor 1 and then sensor 2 is
        # allowed to start.
        packet.set("sensor_id", 6)
        packet.set("timestamp", time.time())

        self.scheduler.synchronize(packet)

        round_complete = (self.number_of_sensors - packet.get("sensor_id") + 1) * self.slot_time
        expected = packet.get("timestamp") + round_complete + ((self.id - 1) * self.slot_time)
        self.assertAlmostEqual(self.scheduler.timestamp, expected,
                               delta=self.time_delta)

        # Only future timestamp must be accepted.
        packet.set("timestamp", 0)

        self.scheduler.synchronize(packet)

        self.assertAlmostEqual(self.scheduler.timestamp, expected,
                               delta=self.time_delta)

    def test_shift(self):
        # The schedule must be shited by the provided number of seconds.
        timestamp = self.scheduler.timestamp
        self.scheduler.shift(0.5)
        self.assertEqual(self.scheduler.timestamp, timestamp + 0.5)
