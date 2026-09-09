"""Tests unitaires pour la gestion de l'autostart et de la portabilité."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.system.autostart as autostart_mod
from app.system.autostart import AutostartManager


class TestAutostartManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp_dir.name)
        self.config_dir = self.home / ".config"
        self.autostart_dir = self.config_dir / "autostart"
        self.desktop_file = self.autostart_dir / "wallpapermaison.desktop"
        self.systemd_user_dir = self.config_dir / "systemd" / "user"
        self.systemd_service_file = self.systemd_user_dir / "wallpapermaison.service"
        self.systemd_wants_dir = self.systemd_user_dir / "graphical-session.target.wants"

        self.orig_autostart_dir = autostart_mod.AUTOSTART_DIR
        self.orig_desktop_file = autostart_mod.DESKTOP_ENTRY_FILE
        self.orig_systemd_dir = autostart_mod.SYSTEMD_USER_DIR
        self.orig_systemd_file = autostart_mod.SYSTEMD_SERVICE_FILE
        self.orig_wants_dir = autostart_mod.SYSTEMD_WANTS_DIR

        autostart_mod.AUTOSTART_DIR = self.autostart_dir
        autostart_mod.DESKTOP_ENTRY_FILE = self.desktop_file
        autostart_mod.SYSTEMD_USER_DIR = self.systemd_user_dir
        autostart_mod.SYSTEMD_SERVICE_FILE = self.systemd_service_file
        autostart_mod.SYSTEMD_WANTS_DIR = self.systemd_wants_dir

        self.mgr = AutostartManager()

    def tearDown(self):
        autostart_mod.AUTOSTART_DIR = self.orig_autostart_dir
        autostart_mod.DESKTOP_ENTRY_FILE = self.orig_desktop_file
        autostart_mod.SYSTEMD_USER_DIR = self.orig_systemd_dir
        autostart_mod.SYSTEMD_SERVICE_FILE = self.orig_systemd_file
        autostart_mod.SYSTEMD_WANTS_DIR = self.orig_wants_dir
        self.tmp_dir.cleanup()

    def test_initially_disabled(self):
        self.assertFalse(self.mgr.is_enabled())

    def test_enable_creates_files(self):
        with patch("subprocess.run"):
            success = self.mgr.set_enabled(True)
            self.assertTrue(success)
            self.assertTrue(self.desktop_file.exists())
            self.assertTrue(self.systemd_service_file.exists())
            self.assertTrue((self.systemd_wants_dir / "wallpapermaison.service").is_symlink())
            self.assertTrue(self.mgr.is_enabled())

    def test_disable_removes_files(self):
        with patch("subprocess.run"):
            self.mgr.set_enabled(True)
            self.assertTrue(self.mgr.is_enabled())
            self.mgr.set_enabled(False)
            self.assertFalse(self.desktop_file.exists())
            self.assertFalse(self.systemd_service_file.exists())
            self.assertFalse(self.mgr.is_enabled())


if __name__ == "__main__":
    unittest.main()
