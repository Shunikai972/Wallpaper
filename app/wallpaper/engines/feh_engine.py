"""Moteur statique léger sous X11 via feh."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.feh")

class FehWallpaperEngine(BaseWallpaperEngine):
    """Applique les fonds d'écran statiques via feh sur X11."""

    @property
    def name(self) -> str:
        return "feh"

    @property
    def display_name(self) -> str:
        return "feh (Statique X11)"

    @property
    def supported_types(self) -> List[str]:
        return ["image"]

    def is_available(self) -> bool:
        has_feh = bool(shutil.which("feh"))
        is_x11 = bool(os.environ.get("DISPLAY"))
        return bool(has_feh and is_x11)

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False

        options = options or {}
        fit_mode = options.get("fit_mode", "fill")
        flag = "--bg-fill"
        if fit_mode == "fit":
            flag = "--bg-max"
        elif fit_mode == "stretch":
            flag = "--bg-scale"
        elif fit_mode == "center":
            flag = "--bg-center"

        try:
            subprocess.run(["feh", flag, str(p)], check=True, timeout=3)
            logger.info("Fond d'écran appliqué via feh: %s", p.name)
            return True
        except Exception as e:
            logger.error("Erreur lors de l'application via feh: %s", e)
            return False
