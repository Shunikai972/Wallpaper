"""Moteur de secours / simulateur gracieux avec notifications de diagnostic."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.fallback")

class FallbackWallpaperEngine(BaseWallpaperEngine):
    """Moteur de secours garantissant le fonctionnement sans crash sur tout environnement."""

    def __init__(self) -> None:
        self._current_wallpaper: Optional[str] = None
        self._is_paused = False

    @property
    def name(self) -> str:
        return "fallback"

    @property
    def display_name(self) -> str:
        return "Mode Diagnostic / Simulation"

    @property
    def supported_types(self) -> List[str]:
        return ["image", "gif", "video"]

    def is_available(self) -> bool:
        return True

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path)
        self._current_wallpaper = str(p)
        self._is_paused = False
        logger.info("[FALLBACK ENGINE] Fond d'écran sélectionné pour l'écran '%s': %s (options: %s)",
                    monitor, p.name if p.exists() else wallpaper_path, options)
        return True

    def pause(self, monitor: str = "all") -> bool:
        self._is_paused = True
        logger.info("[FALLBACK ENGINE] Pause demandée.")
        return True

    def resume(self, monitor: str = "all") -> bool:
        self._is_paused = False
        logger.info("[FALLBACK ENGINE] Reprise demandée.")
        return True

    def stop(self, monitor: str = "all") -> bool:
        self._current_wallpaper = None
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": True,
            "supported_types": self.supported_types,
            "is_running": bool(self._current_wallpaper),
            "is_paused": self._is_paused,
            "current_file": self._current_wallpaper
        }
