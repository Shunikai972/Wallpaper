"""Moteur natif GNOME via GSettings (Fedora par défaut)."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.gnome")

class GnomeWallpaperEngine(BaseWallpaperEngine):
    """Applique les fonds d'écran sous GNOME en modifiant GSettings."""

    @property
    def name(self) -> str:
        return "gnome"

    @property
    def display_name(self) -> str:
        return "GNOME (GSettings Natif)"

    @property
    def supported_types(self) -> List[str]:
        return ["image", "gif"]

    def is_available(self) -> bool:
        return bool(shutil.which("gsettings")) and ("gnome" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower() or "gnome" in os.environ.get("DESKTOP_SESSION", "").lower())

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            logger.error("Fichier introuvable: %s", p)
            return False

        file_uri = f"file://{p}"
        fit_mode = (options or {}).get("fit_mode", "zoom") # 'zoom', 'scaled', 'centered', 'stretched'
        if fit_mode == "fill":
            fit_mode = "zoom"
        elif fit_mode == "fit":
            fit_mode = "scaled"
        elif fit_mode == "stretch":
            fit_mode = "stretched"
        elif fit_mode == "center":
            fit_mode = "centered"

        try:
            # Mode clair et sombre
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", file_uri], check=True, timeout=3)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", file_uri], check=True, timeout=3)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-options", fit_mode], check=True, timeout=3)
            logger.info("Fond d'écran appliqué via GNOME GSettings: %s (mode: %s)", p.name, fit_mode)
            return True
        except Exception as e:
            logger.error("Erreur lors de l'application via GSettings: %s", e)
            return False
