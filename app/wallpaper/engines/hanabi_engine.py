"""Moteur natif GNOME Shell via l'extension Hanabi (intègre la vidéo directement dans le compositeur Mutter)."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.hanabi")

class HanabiWallpaperEngine(BaseWallpaperEngine):
    """Contrôle la vidéo de fond directement intégrée dans GNOME Shell via l'extension Hanabi."""

    SCHEMA = "io.github.jeffshee.hanabi-extension"
    UUID = "hanabi-extension@jeffshee.github.io"

    def __init__(self) -> None:
        self._current_wallpaper: Optional[str] = None
        self._is_paused = False

    @property
    def name(self) -> str:
        return "hanabi"

    @property
    def display_name(self) -> str:
        return "GNOME Shell Intégré (Extension Hanabi)"

    @property
    def supported_types(self) -> List[str]:
        return ["video"]

    def is_available(self) -> bool:
        if not shutil.which("gsettings") or not shutil.which("gnome-extensions"):
            return False
        try:
            res = subprocess.run(["gsettings", "list-keys", self.SCHEMA], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode != 0:
                return False
            ext_res = subprocess.run(["gnome-extensions", "info", self.UUID], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if "ENABLED" in ext_res.stdout or "ACTIVE" in ext_res.stdout:
                return True
        except Exception:
            pass
        return False

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False
        try:
            subprocess.run(["gsettings", "set", self.SCHEMA, "video-path", str(p)], check=True)
            self._current_wallpaper = str(p)
            self._is_paused = False
            logger.info("Vidéo transmise directement au compositeur GNOME Shell via Hanabi: %s", p.name)
            return True
        except Exception as e:
            logger.error("Erreur lors de l'application via Hanabi: %s", e)
            return False

    def pause(self, monitor: str = "all") -> bool:
        self._is_paused = True
        return True

    def resume(self, monitor: str = "all") -> bool:
        self._is_paused = False
        return True

    def stop(self, monitor: str = "all") -> bool:
        try:
            subprocess.run(["gsettings", "set", self.SCHEMA, "video-path", ""], check=False)
        except Exception:
            pass
        self._current_wallpaper = None
        self._is_paused = False
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": self.is_available(),
            "supported_types": self.supported_types,
            "is_running": bool(self._current_wallpaper),
            "is_paused": self._is_paused,
            "current_file": self._current_wallpaper
        }
