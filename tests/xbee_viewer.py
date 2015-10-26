import unittest
from mock import patch
from ..settings import Settings
from ..zigbee.XBee_Viewer import XBee_Viewer

class TestXBeeViewer(unittest.TestCase):
    def setUp(self):
        self.settings = Settings("tests/settings.json", "xbee_viewer")
        self.viewer = XBee_Viewer(self.settings)

    def test_initialization(self):
        # There should be no points and arrows.
        self.assertEqual(self.viewer.points, [])
        self.assertEqual(self.viewer.arrows, [])

    @patch("matplotlib.pyplot.show")
    def test_draw_points(self, mock_show):
        # There should be n + 1 points, where n is the total number of
        # sensors in the network. The additional point is the ground station.
        # We do not test how they are drawn exactly as that may differ.
        self.viewer.draw_points()
        self.assertEqual(len(self.viewer.points), self.settings.get("number_of_sensors") + 1)

    @patch("matplotlib.pyplot.show")
    def test_draw_arrow(self, mock_show):
        # Newly drawn arrows must be added to the arrow list.
        # Again we do not test how they are actually drawn as that may differ.
        self.viewer.draw_points()

        self.viewer.draw_arrow(2, 5)
        self.assertEqual(len(self.viewer.arrows), 1)

        self.viewer.draw_arrow(3, 4)
        self.assertEqual(len(self.viewer.arrows), 2)

    @patch("matplotlib.pyplot.show")
    def test_clear_arrows(self, mock_show):
        # The arrows list must be empty.
        self.viewer.draw_points()
        self.viewer.draw_arrow(2, 5)
        self.viewer.clear_arrows()
        self.assertEqual(len(self.viewer.arrows), 0)
