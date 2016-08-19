import unittest
from dronekit import LocationLocal
from mock import patch, PropertyMock
from ..environment.Location_Proxy import Location_Proxy
from ..geometry.Geometry import Geometry

class TestEnvironmentLocationProxy(unittest.TestCase):
    def setUp(self):
        self.geometry = Geometry()
        self.proxy = Location_Proxy(self.geometry)

    def test_initialization(self):
        proxy = Location_Proxy(self.geometry)
        self.assertEqual(proxy._geometry, self.geometry)

        # The `geometry` argument must be a `Geometry` object.
        with self.assertRaises(TypeError):
            Location_Proxy(None)

    def test_geometry(self):
        self.assertEqual(self.proxy.geometry, self.geometry)

    def test_location(self):
        with self.assertRaises(NotImplementedError):
            dummy = self.proxy.location

    @patch.object(Geometry, "get_location_meters")
    @patch.object(Location_Proxy, "location", new_callable=PropertyMock)
    def test_get_location(self, location_mock, get_location_meters_mock):
        location = self.proxy.get_location()
        location_mock.assert_called_once_with()
        get_location_meters_mock.assert_called_once_with(location_mock.return_value, 0, 0, 0)
        self.assertEqual(location, get_location_meters_mock.return_value)

        location_mock.reset_mock()
        get_location_meters_mock.reset_mock()
        location = self.proxy.get_location(1, 2, 3)
        location_mock.assert_called_once_with()
        get_location_meters_mock.assert_called_once_with(location_mock.return_value, 1, 2, 3)
        self.assertEqual(location, get_location_meters_mock.return_value)

    @patch.object(Geometry, "get_distance_meters")
    @patch.object(Location_Proxy, "location", new_callable=PropertyMock)
    def test_get_distance(self, location_mock, get_distance_meters_mock):
        location = LocationLocal(5.0, 6.0, -7.0)
        distance = self.proxy.get_distance(location)
        location_mock.assert_called_once_with()
        get_distance_meters_mock.assert_called_once_with(location_mock.return_value, location)
        self.assertEqual(distance, get_distance_meters_mock.return_value)
