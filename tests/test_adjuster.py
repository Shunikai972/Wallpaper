"""Tests unitaires pour le pipeline de retouche d'image non destructif."""

import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.image_processing.adjuster import ImageAdjuster

class TestImageAdjuster(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.adjuster = ImageAdjuster()
        self.adjuster.output_dir = Path(self.temp_dir.name)

        # Création d'une image de test synthétique 200x200
        self.test_img_path = Path(self.temp_dir.name) / "sample.jpg"
        img = Image.new("RGB", (200, 200), color=(120, 160, 200))
        img.save(self.test_img_path, "JPEG")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_apply_brightness_contrast(self):
        adj = {
            "brightness": 1.5,
            "contrast": 1.2,
            "saturation": 1.1
        }
        res_path = self.adjuster.apply_adjustments(self.test_img_path, adj)
        self.assertTrue(Path(res_path).exists())
        self.assertNotEqual(res_path, str(self.test_img_path))

    def test_apply_black_and_white(self):
        adj = {"black_and_white": True}
        res_path = self.adjuster.apply_adjustments(self.test_img_path, adj)
        self.assertTrue(Path(res_path).exists())
        with Image.open(res_path) as im:
            r, g, b = im.getpixel((50, 50))
            self.assertEqual(r, g)
            self.assertEqual(g, b)

    def test_apply_rotation(self):
        # Création d'une image rectangulaire 100x200
        rect_path = Path(self.temp_dir.name) / "rect.jpg"
        Image.new("RGB", (100, 200), color=(255, 0, 0)).save(rect_path)

        adj = {"rotate": 90}
        res_path = self.adjuster.apply_adjustments(rect_path, adj)
        with Image.open(res_path) as im:
            self.assertEqual(im.size, (200, 100))

    def test_apply_vignette(self):
        adj = {"vignette": 0.5}
        res_path = self.adjuster.apply_adjustments(self.test_img_path, adj)
        self.assertTrue(Path(res_path).exists())

if __name__ == "__main__":
    unittest.main()
