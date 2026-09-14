"""Tests pour le module d'optimisation vidéo fluide."""

import os
import unittest
from pathlib import Path

from app.wallpaper.video_optimizer import VideoOptimizer, video_optimizer


class TestVideoOptimizer(unittest.TestCase):
    """Vérifie le bon fonctionnement du cache et de l'optimiseur vidéo."""

    def setUp(self) -> None:
        self.optimizer = VideoOptimizer()

    def test_ffmpeg_binary_detection(self) -> None:
        binary = self.optimizer.get_ffmpeg_binary()
        self.assertTrue(isinstance(binary, str))
        self.assertTrue(len(binary) > 0)

    def test_get_optimized_path_nonexistent(self) -> None:
        res = self.optimizer.get_optimized_path("/nonexistent/video/test.mp4")
        self.assertIsNone(res)

    def test_get_optimized_path_existing(self) -> None:
        # denji-hunter.3840x2160.mp4 has been optimized into cache
        cache_file = Path.home() / ".cache/wallpapermaison/optimized/denji-hunter.3840x2160.mp4"
        if cache_file.exists():
            res = self.optimizer.get_optimized_path("/some/path/denji-hunter.3840x2160.mp4")
            self.assertIsNotNone(res)
            self.assertTrue(res.endswith("denji-hunter.3840x2160.mp4"))

    def test_get_playable_path_fallback(self) -> None:
        dummy = "/fake/path/image.png"
        res = self.optimizer.get_playable_path(dummy, auto_optimize=False)
        self.assertEqual(res, dummy)


if __name__ == "__main__":
    unittest.main()
