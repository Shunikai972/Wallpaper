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
        if not shutil.which("gsettings"):
            return False
        try:
            # 1. Vérifier que le schéma GSettings de Hanabi est présent
            res = subprocess.run(
                ["gsettings", "list-keys", self.SCHEMA],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if res.returncode != 0:
                return False

            # 2. Vérifier que les fichiers de l'extension sont présents (local ou système)
            ext_path = Path.home() / ".local/share/gnome-shell/extensions" / self.UUID
            sys_ext_path = Path("/usr/share/gnome-shell/extensions") / self.UUID
            if not ext_path.exists() and not sys_ext_path.exists():
                return False

            # 3. Vérifier que l'extension est activée dans org.gnome.shell
            g_enabled = subprocess.run(
                ["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            if self.UUID in g_enabled.stdout:
                return True

            # 4. Fallback sur gnome-extensions info (tolérant localisation FR/EN)
            if shutil.which("gnome-extensions"):
                ext_res = subprocess.run(
                    ["gnome-extensions", "info", self.UUID],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                out = ext_res.stdout.upper()
                if any(k in out for k in ["ENABLED", "ACTIVE", "ACTIF", "ACTIVÉ"]):
                    return True
        except Exception:
            pass
        return False

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False
        try:
            # 1. Met à jour le fond d'écran statique GNOME pour un rendu immédiat et sans scintillement
            try:
                from app.wallpaper.engines.gnome_engine import GnomeWallpaperEngine
                GnomeWallpaperEngine().apply(str(p), monitor=monitor, options=options)
            except Exception as e:
                logger.debug("Mise à jour miniature statique GNOME: %s", e)

            # 2. Définir le chemin de la vidéo dans les paramètres GSettings de Hanabi
            subprocess.run(["gsettings", "set", self.SCHEMA, "video-path", str(p)], check=True)
            self._current_wallpaper = str(p)
            self._is_paused = False

            # 3. S'assurer que l'extension GNOME Shell Hanabi est activée
            if shutil.which("gnome-extensions"):
                subprocess.run(["gnome-extensions", "enable", self.UUID], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 4. Relauncher le processus renderer pour prise en compte immédiate
            subprocess.run(["pkill", "-f", "hanabi-extension.*renderer.js"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
