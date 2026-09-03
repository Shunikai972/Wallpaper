"""Moteur de fond d'écran Wayland via swww (GIFs et transitions animées)."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.swww")

class SwwwWallpaperEngine(BaseWallpaperEngine):
    """Gère l'affichage sous Wayland avec swww."""

    def __init__(self) -> None:
        self._daemon_started = False

    @property
    def name(self) -> str:
        return "swww"

    @property
    def display_name(self) -> str:
        return "swww (GIFs & Transitions Wayland)"

    @property
    def supported_types(self) -> List[str]:
        return ["image", "gif"]

    def is_available(self) -> bool:
        has_bin = bool(shutil.which("swww"))
        is_wayland = os.environ.get("WAYLAND_DISPLAY") or "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        return bool(has_bin and is_wayland)

    def _ensure_daemon(self) -> bool:
        if not self.is_available():
            return False
        # Vérification si le démon répond
        res = subprocess.run(["swww", "query"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            try:
                subprocess.Popen(["swww-daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Démon swww-daemon initialisé.")
                return True
            except Exception as e:
                logger.error("Impossible de démarrer swww-daemon: %s", e)
                return False
        return True

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False

        if not self._ensure_daemon():
            return False

        options = options or {}
        transition_type = options.get("transition_type", "fade") # fade, wipe, wave, grow, outer
        fps = options.get("max_fps", 30)

        cmd = [
            "swww", "img", str(p),
            "--transition-type", transition_type,
            "--transition-fps", str(fps),
            "--transition-duration", "1"
        ]
        if monitor != "all":
            cmd.extend(["-o", monitor])

        try:
            subprocess.run(cmd, check=True, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Fond d'écran appliqué via swww: %s", p.name)
            return True
        except Exception as e:
            logger.error("Erreur commande swww: %s", e)
            return False

    def stop(self, monitor: str = "all") -> bool:
        # swww conserve l'image sans surcoût
        return True
