import unittest
from PIL import Image
from app.image_processing.colorimetry import (
    rgb_to_hsv, hsv_to_rgb, rgb_to_lab, delta_e,
    relative_luminance, contrast_ratio, ensure_contrast,
    lerp_color, ColorPaletteExtractor, build_vscode_color_customizations
)

class TestColorimetry(unittest.TestCase):
    def test_rgb_hsv_roundtrip(self):
        rgb = (120, 200, 50)
        h, s, v = rgb_to_hsv(*rgb)
        rgb_back = hsv_to_rgb(h, s, v)
        self.assertEqual(rgb, rgb_back)

    def test_contrast_ratio_wcag(self):
        # Black and white ratio must be 21:1
        ratio = contrast_ratio((0, 0, 0), (255, 255, 255))
        self.assertAlmostEqual(ratio, 21.0, places=1)

    def test_ensure_contrast_enforcement(self):
        bg = (20, 20, 20)
        poor_fg = (40, 40, 40)
        good_fg = ensure_contrast(poor_fg, bg, min_contrast=7.0)
        ratio = contrast_ratio(good_fg, bg)
        self.assertGreaterEqual(ratio, 7.0)

    def test_lerp_color(self):
        c1 = (0, 0, 0)
        c2 = (100, 200, 50)
        mid = lerp_color(c1, c2, 0.5)
        self.assertEqual(mid, (50, 100, 25))

    def test_palette_extraction(self):
        # Create a test image with dominant red and blue
        img = Image.new("RGB", (100, 100), color=(180, 40, 40))
        extractor = ColorPaletteExtractor(target_resolution=(40, 40))
        palette = extractor.extract_from_image(img)
        self.assertIn("dominant", palette)
        self.assertIn("accent", palette)
        self.assertIn("editor_background", palette)
        self.assertGreaterEqual(palette["contrast_ratio"], 4.5)

    def test_vscode_customizations(self):
        img = Image.new("RGB", (50, 50), color=(30, 90, 180))
        palette = ColorPaletteExtractor().extract_from_image(img)
        colors = build_vscode_color_customizations(palette, mode="full")
        self.assertIn("editor.background", colors)
        self.assertIn("editor.foreground", colors)
        self.assertIn("editorCursor.foreground", colors)
        self.assertIn("statusBar.background", colors)

if __name__ == "__main__":
    unittest.main()
