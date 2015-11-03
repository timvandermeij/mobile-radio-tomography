import unittest
from mock import patch, MagicMock
from ..settings import Settings

class TestXBeeViewer(unittest.TestCase):
    def setUp(self):
        # We need to mock the Matplotlib module as we do not want to use
        # plotting facilities during the tests.
        self.matplotlib_mock = MagicMock()
        modules = {
            'matplotlib': self.matplotlib_mock,
            'matplotlib.pyplot': self.matplotlib_mock.pyplot
        }

        self.patcher = patch.dict('sys.modules', modules)
        self.patcher.start()
        from ..zigbee.XBee_Viewer import XBee_Viewer
        self.settings = Settings("tests/settings.json", "xbee_viewer")
        self.viewer = XBee_Viewer(self.settings)

    def test_initialization(self):
        # There should be no points and arrows.
        self.assertEqual(self.viewer.points, [])
        self.assertEqual(self.viewer.arrows, [])

    def test_draw_points(self):
        # There should be n + 1 points, where n is the total number of
        # sensors in the network. The additional point is the ground station.
        # We do not test how they are drawn exactly as that may differ.
        self.viewer.draw_points()
        self.assertEqual(len(self.viewer.points), self.settings.get("number_of_sensors") + 1)

    def test_draw_arrow(self):
        # Newly drawn arrows must be added to the arrow list.
        # Again we do not test how they are actually drawn as that may differ.
        self.viewer.draw_points()

        self.viewer.draw_arrow(2, 5)
        self.assertEqual(len(self.viewer.arrows), 1)

        self.viewer.draw_arrow(3, 4)
        self.assertEqual(len(self.viewer.arrows), 2)

    def test_clear_arrows(self):
        # The arrows list must be empty.
        self.viewer.draw_points()
        self.viewer.draw_arrow(2, 5)
        self.viewer.clear_arrows()
        self.assertEqual(len(self.viewer.arrows), 0)
