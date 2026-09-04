"""Tests unitaires pour l'orchestrateur de fonds d'écran."""

import unittest
from app.wallpaper.manager import WallpaperManager

class TestWallpaperManager(unittest.TestCase):
    def setUp(self):
        self.mgr = WallpaperManager()

    def test_engine_registration(self):
        self.assertIn("gnome", self.mgr.engines)
        self.assertIn("kde", self.mgr.engines)
        self.assertIn("hanabi", self.mgr.engines)
        self.assertIn("mpvpaper", self.mgr.engines)
        self.assertIn("gtk_video", self.mgr.engines)
        self.assertIn("swww", self.mgr.engines)
        self.assertIn("fallback", self.mgr.engines)

    def test_fallback_engine_always_available(self):
        fallback = self.mgr.engines["fallback"]
        self.assertTrue(fallback.is_available())

    def test_select_engine_fallback_when_tools_missing(self):
        engine = self.mgr.select_engine_for("video")
        self.assertIsNotNone(engine)

    def test_engines_status_reporting(self):
        status_list = self.mgr.get_engines_status()
        self.assertGreater(len(status_list), 0)
        names = [s["name"] for s in status_list]
        self.assertIn("fallback", names)

if __name__ == "__main__":
    unittest.main()
