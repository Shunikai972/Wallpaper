"""Gestion du lancement automatique au démarrage sous Linux (XDG Autostart)."""

import logging
import os
import sys
from pathlib import Path

from app.core.config import HOME

logger = logging.getLogger("wallpapermaison.autostart")

AUTOSTART_DIR = HOME / ".config" / "autostart"
DESKTOP_ENTRY_FILE = AUTOSTART_DIR / "wallpapermaison.desktop"

class AutostartManager:
    """Active ou désactive l'entrée XDG Autostart."""
    def is_enabled(self) -> bool:
        return DESKTOP_ENTRY_FILE.exists()

    def set_enabled(self, enabled: bool) -> bool:
        try:
            if enabled:
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                if getattr(sys, "frozen", False):
                    exec_cmd = f"{sys.executable} --minimized"
                else:
                    main_script = Path(__file__).resolve().parent.parent / "main.py"
                    exec_cmd = f"{sys.executable} {main_script} --minimized"

                content = f"""[Desktop Entry]
Type=Application
Name=WallpaperMaison
Comment=Gestionnaire moderne de fonds d'écran animé
Exec={exec_cmd}
Icon=preferences-desktop-wallpaper
Terminal=false
Categories=Utility;Settings;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
                with open(DESKTOP_ENTRY_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
                os.chmod(DESKTOP_ENTRY_FILE, 0o755)
                logger.info("Autostart activé: %s", DESKTOP_ENTRY_FILE)
            else:
                if DESKTOP_ENTRY_FILE.exists():
                    DESKTOP_ENTRY_FILE.unlink()
                logger.info("Autostart désactivé.")
            return True
        except Exception as e:
            logger.error("Erreur lors de la mise à jour de l'autostart: %s", e)
            return False

autostart_manager = AutostartManager()
