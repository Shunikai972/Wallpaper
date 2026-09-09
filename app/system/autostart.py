"""Gestion du lancement automatique au démarrage sous Linux (XDG Autostart et systemd --user)."""

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
SYSTEMD_USER_DIR = HOME / ".config" / "systemd" / "user"
SYSTEMD_SERVICE_FILE = SYSTEMD_USER_DIR / "wallpapermaison.service"
SYSTEMD_WANTS_DIR = SYSTEMD_USER_DIR / "graphical-session.target.wants"

class AutostartManager:
    """Gère de façon robuste et portable le démarrage automatique via XDG Autostart et systemd."""

    def is_enabled(self) -> bool:
        desktop_ok = DESKTOP_ENTRY_FILE.exists()
        service_ok = SYSTEMD_SERVICE_FILE.exists() and (SYSTEMD_WANTS_DIR / "wallpapermaison.service").exists()
        return desktop_ok or service_ok

    def set_enabled(self, enabled: bool) -> bool:
        try:
            run_script = REPO_ROOT / "scripts" / "run.sh"
            portable_exec = f'sh -c \'for p in "$HOME/reseau/Perso/Bureau/Wallpaper" "$HOME/reseau/Perso/Wallpaper" "$HOME/Wallpaper" "{REPO_ROOT}"; do if [ -x "$p/scripts/run.sh" ]; then exec "$p/scripts/run.sh" --daemon; fi; done\''

            if enabled:
                # 1. XDG Autostart .desktop
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=WallpaperMaison Daemon
Comment=Démarrage automatique et restauration de vos fonds d'écran
Exec={portable_exec}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
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

                # 2. Service systemd --user
                SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
                SYSTEMD_WANTS_DIR.mkdir(parents=True, exist_ok=True)
                systemd_content = f"""[Unit]
Description=WallpaperMaison Service de Fond d'Écran
After=graphical-session.target gnome-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={run_script} --daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
"""
                with open(SYSTEMD_SERVICE_FILE, "w", encoding="utf-8") as f:
                    f.write(systemd_content)

                wants_link = SYSTEMD_WANTS_DIR / "wallpapermaison.service"
                if not wants_link.exists():
                    try:
                        wants_link.symlink_to(SYSTEMD_SERVICE_FILE)
                    except Exception:
                        pass

                # Rechargement de systemd
                subprocess.run(["systemctl", "--user", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Démarrage automatique activé (XDG Autostart + systemd user).")
            else:
                # Désactivation
                if DESKTOP_ENTRY_FILE.exists():
                    DESKTOP_ENTRY_FILE.unlink()
                if (SYSTEMD_WANTS_DIR / "wallpapermaison.service").exists():
                    (SYSTEMD_WANTS_DIR / "wallpapermaison.service").unlink()
                if SYSTEMD_SERVICE_FILE.exists():
                    SYSTEMD_SERVICE_FILE.unlink()

                if PERSISTENT_ROOT and PERSISTENT_ROOT.exists():
                    p_desktop = PERSISTENT_ROOT / ".config" / "autostart" / "wallpapermaison.desktop"
                    if p_desktop.exists():
                        p_desktop.unlink()

                subprocess.run(["systemctl", "--user", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Démarrage automatique désactivé.")

            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'autostart: {e}")
            return False

autostart_manager = AutostartManager()
