"""Gestion du démarrage automatique dans chaque session graphique via XDG Autostart."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import HOME, REPO_ROOT, PERSISTENT_ROOT

logger = logging.getLogger("wallpapermaison.autostart")

AUTOSTART_DIR = HOME / ".config" / "autostart"
DESKTOP_ENTRY_FILE = AUTOSTART_DIR / "wallpapermaison.desktop"
SESSION_STARTER = HOME / ".local" / "bin" / "wallpapermaison-session-start"
SYSTEMD_USER_DIR = HOME / ".config" / "systemd" / "user"
SYSTEMD_SERVICE_FILE = SYSTEMD_USER_DIR / "wallpapermaison.service"
SYSTEMD_WANTS_FILE = SYSTEMD_USER_DIR / "graphical-session.target.wants" / "wallpapermaison.service"


def _remove_legacy_systemd_autostart() -> None:
    """Remove the old single-user-manager service; XDG starts once per login session."""
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", "wallpapermaison.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    for path in (SYSTEMD_WANTS_FILE, SYSTEMD_SERVICE_FILE):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Impossible de retirer l'ancien autostart systemd: %s", path, exc_info=True)

    if PERSISTENT_ROOT and PERSISTENT_ROOT.exists():
        for path in (
            PERSISTENT_ROOT / ".config/systemd/user/graphical-session.target.wants/wallpapermaison.service",
            PERSISTENT_ROOT / ".config/systemd/user/wallpapermaison.service",
        ):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

class AutostartManager:
    """Gère de façon robuste et portable le démarrage automatique via XDG Autostart et systemd."""

    def is_enabled(self) -> bool:
        return DESKTOP_ENTRY_FILE.exists()

    def set_enabled(self, enabled: bool) -> bool:
        try:
            if enabled:
                _remove_legacy_systemd_autostart()
                # The small local bootstrap survives until the persistent project
                # directory is mounted and then launches the daemon in this session.
                source_starter = REPO_ROOT / "scripts" / "session-start.sh"
                if source_starter.is_file():
                    SESSION_STARTER.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_starter, SESSION_STARTER)
                    os.chmod(SESSION_STARTER, 0o755)

                # XDG Autostart is evaluated separately by each graphical login.
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=WallpaperMaison Daemon
Comment=Démarrage automatique et restauration de vos fonds d'écran
Exec={SESSION_STARTER} --daemon
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
"""
                with open(DESKTOP_ENTRY_FILE, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
                os.chmod(DESKTOP_ENTRY_FILE, 0o755)

                # Copie dans le stockage persistant si disponible
                if PERSISTENT_ROOT and PERSISTENT_ROOT.exists():
                    p_autostart = PERSISTENT_ROOT / ".config" / "autostart"
                    p_autostart.mkdir(parents=True, exist_ok=True)
                    with open(p_autostart / "wallpapermaison.desktop", "w", encoding="utf-8") as f:
                        f.write(desktop_content)

                logger.info("Démarrage automatique XDG configuré pour chaque session graphique.")
            else:
                _remove_legacy_systemd_autostart()
                if DESKTOP_ENTRY_FILE.exists():
                    DESKTOP_ENTRY_FILE.unlink()

                if PERSISTENT_ROOT and PERSISTENT_ROOT.exists():
                    p_desktop = PERSISTENT_ROOT / ".config" / "autostart" / "wallpapermaison.desktop"
                    if p_desktop.exists():
                        p_desktop.unlink()

                logger.info("Démarrage automatique désactivé.")

            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'autostart: {e}")
            return False

autostart_manager = AutostartManager()
