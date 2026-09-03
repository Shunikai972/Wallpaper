"""Tests unitaires pour l'API Bridge PyWebView."""

import unittest
from app.api.bridge import AppBridge
from app.storage.database import db

class TestAppBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = AppBridge()

    def test_get_wallpapers_returns_success(self):
        res = self.bridge.get_wallpapers()
        self.assertTrue(res["success"])
        self.assertIsInstance(res["data"], list)

    def test_get_stats_returns_dict(self):
        res = self.bridge.get_stats()
        self.assertTrue(res["success"])
        self.assertIn("total", res["data"])
        self.assertIn("favorites", res["data"])

    def test_get_config_and_update(self):
        res = self.bridge.get_config()
        self.assertTrue(res["success"])

        up_res = self.bridge.update_config("performance_profile", "Balanced")
        self.assertTrue(up_res["success"])

    def test_get_monitors(self):
        res = self.bridge.get_monitors()
        self.assertTrue(res["success"])
        self.assertIsInstance(res["data"], list)
        self.assertGreater(len(res["data"]), 0)

    def test_get_system_info(self):
        res = self.bridge.get_system_info()
        self.assertTrue(res["success"])
        self.assertIn("distro", res["data"])
        self.assertIn("tools", res["data"])

    def test_playlists_crud_bridge(self):
        res = self.bridge.get_playlists()
        self.assertTrue(res["success"])

        create_res = self.bridge.create_playlist("Test Playlist Bridge", "Description", "folder", 300, 0)
        self.assertTrue(create_res["success"])
        pid = create_res["id"]

        del_res = self.bridge.delete_playlist(pid)
        self.assertTrue(del_res["success"])

if __name__ == "__main__":
    unittest.main()
