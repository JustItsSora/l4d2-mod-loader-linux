import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import l4d2_app_config as config


class WindowGeometryTests(unittest.TestCase):
    def geometry(self, screen):
        work = (0, 0, screen[0], screen[1]) if screen else None
        with mock.patch.object(config, "IS_WINDOWS", False), \
                mock.patch.object(config, "_linux_screen_size",
                                  return_value=screen), \
                mock.patch.object(config, "_linux_work_area",
                                  return_value=work):
            return config.window_geometry()

    def test_window_fits_on_screen(self):
        geometry = self.geometry((1366, 768))
        self.assertLessEqual(geometry["width"], 1366)
        self.assertLessEqual(geometry["height"], 768)
        self.assertLessEqual(geometry["left"] + geometry["width"], 1366)
        self.assertLessEqual(geometry["top"] + geometry["height"], 768)
        self.assertGreaterEqual(geometry["left"], 0)
        self.assertGreaterEqual(geometry["top"], 0)

    def test_window_fits_on_small_screen(self):
        geometry = self.geometry((1024, 600))
        self.assertLessEqual(geometry["width"], 1024)
        self.assertLessEqual(geometry["height"], 600)
        self.assertLessEqual(geometry["left"] + geometry["width"], 1024)
        self.assertLessEqual(geometry["top"] + geometry["height"], 600)

    def test_fallback_when_screen_is_unknown(self):
        geometry = self.geometry(None)
        self.assertGreaterEqual(geometry["width"], 640)
        self.assertGreaterEqual(geometry["height"], 480)
        self.assertLessEqual(geometry["height"], config.FALLBACK_SCREEN[1])

    def test_window_is_not_taller_than_screen(self):
        geometry = self.geometry((1920, 1080))
        self.assertEqual(geometry["width"], config.DEFAULT_WINDOW_WIDTH)
        self.assertEqual(geometry["height"], config.DEFAULT_WINDOW_HEIGHT)


if __name__ == "__main__":
    unittest.main()
