"""Tests unitaires pour env_checker et vscode_sync."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.automation.env_checker import EnvChecker
from app.automation.vscode_sync import VsCodeSync

class TestSyncAndEnv(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_env_parser_valid(self):
        env_file = self.root / ".env"
        env_file.write_text(
            "# Comment\n"
            "wallpaperlink=\"https://example.com/video.mp4\"\n"
            "check_interval=15\n",
            encoding="utf-8"
        )
        checker = EnvChecker(project_root=self.root)
        cfg = checker.read_env_config()
        self.assertEqual(cfg["wallpaperlink"], "https://example.com/video.mp4")
        self.assertEqual(cfg["check_interval"], 15)

    def test_env_parser_empty(self):
        env_file = self.root / ".env"
        env_file.write_text("wallpaperlink=\n", encoding="utf-8")
        checker = EnvChecker(project_root=self.root)
        cfg = checker.read_env_config()
        self.assertEqual(cfg["wallpaperlink"], "")
        self.assertEqual(cfg["check_interval"], 30)

    def test_env_sanitize_filename(self):
        checker = EnvChecker(project_root=self.root)
        clean = checker.sanitize_filename("my/bad:file*name?.mp4")
        self.assertNotIn("/", clean)
        self.assertNotIn(":", clean)
        self.assertNotIn("*", clean)
        self.assertNotIn("?", clean)
        self.assertTrue(clean.endswith(".mp4"))

    @patch("subprocess.run")
    def test_vscode_sync_publish_state(self, mock_run):
        sync = VsCodeSync()
        state_file = self.root / "current_wallpaper.json"
        with patch("app.automation.vscode_sync.STATE_FILE", state_file):
            dummy_video = self.root / "test.mp4"
            dummy_video.write_text("dummy", encoding="utf-8")
            sync.publish_state(str(dummy_video), media_type="video", source="desktop")
            self.assertTrue(state_file.exists())
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(data["path"], str(dummy_video))
            self.assertEqual(data["source"], "desktop")
            self.assertEqual(data["media_type"], "video")

    def test_patch_vscode_html_has_sudo_button(self):
        html_file = Path.home() / ".config/wallpapermaison/vscode/workbench.html"
        if html_file.exists():
            content = html_file.read_text(encoding="utf-8")
            self.assertIn("sudo-root-item", content)
            self.assertIn("openSudoTerminal", content)
            self.assertIn("live-wallpaper-bg-video", content)

    def test_extension_registered_pinned(self):
        ext_file = Path("/var/tmp/visual_extensions/extensions.json")
        if ext_file.exists():
            data = json.loads(ext_file.read_text(encoding="utf-8"))
            lw = next((e for e in data if e.get("identifier", {}).get("id") == "budicuy.live-wallpaper"), None)
            self.assertIsNotNone(lw)
            self.assertEqual(lw.get("version"), "99.0.0")
            self.assertTrue(lw.get("metadata", {}).get("pinned"))

if __name__ == "__main__":
    unittest.main()
