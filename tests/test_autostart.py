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
        self.systemd_wants_file = self.systemd_user_dir / "graphical-session.target.wants" / "wallpapermaison.service"
        self.session_starter = self.home / ".local" / "bin" / "wallpapermaison-session-start"
        self.workspace = self.home / "workspace"
        self.source_starter = self.workspace / "scripts" / "session-start.sh"
        self.source_starter.parent.mkdir(parents=True)
        self.source_starter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

        self.orig_autostart_dir = autostart_mod.AUTOSTART_DIR
        self.orig_desktop_file = autostart_mod.DESKTOP_ENTRY_FILE
        self.orig_systemd_file = autostart_mod.SYSTEMD_SERVICE_FILE
        self.orig_wants_file = autostart_mod.SYSTEMD_WANTS_FILE
        self.orig_session_starter = autostart_mod.SESSION_STARTER
        self.orig_repo_root = autostart_mod.REPO_ROOT
        self.orig_persistent_root = autostart_mod.PERSISTENT_ROOT

        autostart_mod.AUTOSTART_DIR = self.autostart_dir
        autostart_mod.DESKTOP_ENTRY_FILE = self.desktop_file
        autostart_mod.SYSTEMD_SERVICE_FILE = self.systemd_service_file
        autostart_mod.SYSTEMD_WANTS_FILE = self.systemd_wants_file
        autostart_mod.SESSION_STARTER = self.session_starter
        autostart_mod.REPO_ROOT = self.workspace
        autostart_mod.PERSISTENT_ROOT = None

        self.mgr = AutostartManager()

    def tearDown(self):
        autostart_mod.AUTOSTART_DIR = self.orig_autostart_dir
        autostart_mod.DESKTOP_ENTRY_FILE = self.orig_desktop_file
        autostart_mod.SYSTEMD_SERVICE_FILE = self.orig_systemd_file
        autostart_mod.SYSTEMD_WANTS_FILE = self.orig_wants_file
        autostart_mod.SESSION_STARTER = self.orig_session_starter
        autostart_mod.REPO_ROOT = self.orig_repo_root
        autostart_mod.PERSISTENT_ROOT = self.orig_persistent_root
        self.tmp_dir.cleanup()

    def test_initially_disabled(self):
        self.assertFalse(self.mgr.is_enabled())

    def test_enable_creates_files(self):
        with patch("subprocess.run"):
            success = self.mgr.set_enabled(True)
            self.assertTrue(success)
            self.assertTrue(self.desktop_file.exists())
            self.assertTrue(self.session_starter.exists())
            self.assertIn(f"Exec={self.session_starter} --daemon", self.desktop_file.read_text(encoding="utf-8"))
            self.assertFalse(self.systemd_service_file.exists())
            self.assertFalse(self.systemd_wants_file.exists())
            self.assertTrue(self.mgr.is_enabled())

    def test_disable_removes_files(self):
        with patch("subprocess.run"):
            self.mgr.set_enabled(True)
            self.assertTrue(self.mgr.is_enabled())
            self.mgr.set_enabled(False)
            self.assertFalse(self.desktop_file.exists())
            self.assertFalse(self.systemd_service_file.exists())
            self.assertFalse(self.systemd_wants_file.exists())
            self.assertFalse(self.mgr.is_enabled())


if __name__ == "__main__":
    unittest.main()
