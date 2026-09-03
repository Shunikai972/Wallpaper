"""Tests unitaires pour le scan et l'extraction de métadonnées."""

import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.media.metadata import MediaMetadataExtractor
from app.media.thumbnail import ThumbnailGenerator

class TestMediaScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        # Création d'une image test PNG
        self.img_path = self.base_dir / "test_image.png"
        img = Image.new("RGBA", (1920, 1080), color=(50, 100, 150, 255))
        img.save(self.img_path, "PNG")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_metadata_extraction(self):
        meta = MediaMetadataExtractor.extract(self.img_path)
        self.assertEqual(meta["media_type"], "image")
        self.assertEqual(meta["width"], 1920)
        self.assertEqual(meta["height"], 1080)
        self.assertTrue(len(meta["file_hash"]) > 0)

    def test_thumbnail_generation(self):
        generator = ThumbnailGenerator(target_size=(480, 270))
        generator.thumb_dir = self.base_dir / "thumbs"
        generator.thumb_dir.mkdir()

        thumb = generator.generate(self.img_path)
        self.assertTrue(Path(thumb).exists())

        with Image.open(thumb) as im:
            self.assertEqual(im.size, (480, 270))

if __name__ == "__main__":
    unittest.main()
