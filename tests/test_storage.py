"""Tests unitaires pour la couche de persistance SQLite et migrations."""

import tempfile
import unittest
from pathlib import Path

from app.storage.database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_wallpaper.db"
        self.db = Database(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_database_initialization_and_migrations(self):
        conn = self.db._get_connection()
        cursor = conn.execute("SELECT version FROM schema_migrations")
        versions = [r[0] for r in cursor.fetchall()]
        self.assertIn(1, versions)

    def test_wallpapers_crud(self):
        # 1. Insertion
        data = {
            "file_path": "/home/user/Pictures/test_forest.png",
            "file_name": "test_forest.png",
            "file_size": 2048500,
            "file_hash": "abc123hash",
            "media_type": "image",
            "width": 3840,
            "height": 2160,
            "tags": "nature,4k"
        }
        wid = self.db.add_or_update_wallpaper(data)
        self.assertGreater(wid, 0)

        # 2. Lecture
        wp = self.db.get_wallpaper_by_id(wid)
        self.assertIsNotNone(wp)
        self.assertEqual(wp["file_name"], "test_forest.png")
        self.assertEqual(wp["media_type"], "image")
        self.assertEqual(wp["is_favorite"], 0)

        # 3. Toggle favori
        new_fav = self.db.toggle_favorite(wid)
        self.assertTrue(new_fav)
        wp_updated = self.db.get_wallpaper_by_id(wid)
        self.assertEqual(wp_updated["is_favorite"], 1)

        # 4. Tags
        tags = self.db.get_all_tags()
        self.assertIn("nature", tags)
        self.assertIn("4k", tags)

        # 5. Suppression
        self.db.delete_wallpaper(wid)
        self.assertIsNone(self.db.get_wallpaper_by_id(wid))

    def test_playlists_and_items(self):
        pid = self.db.create_playlist("Ambiance Nuit", "Fonds calmes", "moon", 600, 1)
        self.assertGreater(pid, 0)

        # Ajout d'un wallpaper
        wid = self.db.add_or_update_wallpaper({
            "file_path": "/home/user/Pictures/stars.jpg",
            "file_name": "stars.jpg",
            "file_size": 1024,
            "media_type": "image"
        })

        self.db.set_playlist_items(pid, [wid])
        pl = self.db.get_playlist(pid)
        self.assertIsNotNone(pl)
        self.assertEqual(len(pl["items"]), 1)
        self.assertEqual(pl["items"][0]["id"], wid)

    def test_adjustments_storage(self):
        wid = self.db.add_or_update_wallpaper({
            "file_path": "/home/user/Pictures/lake.jpg",
            "file_name": "lake.jpg",
            "file_size": 1024,
            "media_type": "image"
        })

        adj = {
            "brightness": 1.2,
            "contrast": 1.1,
            "saturation": 1.4,
            "black_and_white": 0,
            "sepia": 1,
            "vignette": 0.3
        }
        self.db.save_adjustments(wid, adj)

        saved = self.db.get_adjustments(wid)
        self.assertIsNotNone(saved)
        self.assertAlmostEqual(saved["brightness"], 1.2)
        self.assertAlmostEqual(saved["vignette"], 0.3)
        self.assertEqual(saved["sepia"], 1)

if __name__ == "__main__":
    unittest.main()
