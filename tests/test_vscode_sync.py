"""Tests for media paths published to the VS Code workbench."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.automation import vscode_media
from app.automation.vscode_media import stage_media_for_vscode


class TestVsCodeMediaStaging(unittest.TestCase):
    def test_media_is_copied_under_the_active_extension_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "wallpaper.png"
            extension_root = root / "extensions" / "budicuy.live-wallpaper-99.0.0"
            source.write_bytes(b"video payload")

            with patch.dict(os.environ, {"WALLPAPERMAISON_VSCODE_EXT_DIR": str(extension_root)}):
                staged = Path(stage_media_for_vscode(str(source)))
                staged_again = Path(stage_media_for_vscode(str(source)))

            self.assertEqual(staged.parent, extension_root / "wallpaper-media")
            self.assertEqual(staged.read_bytes(), source.read_bytes())
            self.assertEqual(staged_again, staged)

    def test_videos_are_cached_as_h264_mp4(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "wallpaper.mkv"
            extension_root = root / "extensions" / "budicuy.live-wallpaper-99.0.0"
            source.write_bytes(b"video payload")

            def make_h264(_source, destination):
                destination.write_bytes(b"h264 payload")
                return True

            with patch.dict(os.environ, {"WALLPAPERMAISON_VSCODE_EXT_DIR": str(extension_root)}):
                with patch.object(vscode_media, "_transcode_h264", side_effect=make_h264) as transcode:
                    staged = Path(stage_media_for_vscode(str(source)))
                    staged_again = Path(stage_media_for_vscode(str(source)))

            self.assertEqual(staged.suffix, ".mp4")
            self.assertEqual(staged.read_bytes(), b"h264 payload")
            self.assertEqual(staged_again, staged)
            transcode.assert_called_once()


if __name__ == "__main__":
    unittest.main()
