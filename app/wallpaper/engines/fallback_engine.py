"""Moteur adaptatif de secours pour environnements avec permissions limitées ou sans mpvpaper."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import PROCESSED_DIR
from app.media.metadata import MediaMetadataExtractor
from app.wallpaper.base import BaseWallpaperEngine
from app.wallpaper.engines.gnome_engine import GnomeWallpaperEngine
from app.wallpaper.engines.kde_engine import KdeWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.fallback")

class FallbackWallpaperEngine(BaseWallpaperEngine):
    """Moteur adaptatif garantissant le fonctionnement sans crash sur tout environnement."""

    def __init__(self) -> None:
        self._current_wallpaper: Optional[str] = None
        self._is_paused = False
        self._gnome_engine = GnomeWallpaperEngine()
        self._kde_engine = KdeWallpaperEngine()

    @property
    def name(self) -> str:
        return "fallback"

    @property
    def display_name(self) -> str:
        return "Mode Adapté (Rendu Haute Fidélité)"

    @property
    def supported_types(self) -> List[str]:
        return ["image", "gif", "video"]

    def is_available(self) -> bool:
        return True

    def _extract_video_frame(self, video_path: Path) -> Optional[Path]:
        """Extrait une image clé haute résolution d'une vidéo via ffmpeg."""
        from app.media.media_tools import run_ffmpeg

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        file_hash = MediaMetadataExtractor.calculate_hash(video_path) or f"v_{abs(hash(str(video_path)))}"
        out_frame = PROCESSED_DIR / f"frame_{file_hash}.png"

        if out_frame.exists() and out_frame.stat().st_size > 0:
            return out_frame

        try:
            cmd = [
                "-ss", "00:00:01", "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "1",
                "-y", str(out_frame)
            ]
            if run_ffmpeg(cmd, timeout=10) and out_frame.exists() and out_frame.stat().st_size > 0:
                logger.info("Image clé haute résolution extraite de la vidéo: %s", out_frame.name)
                return out_frame
        except Exception as e:
            logger.warning("Extraction ffmpeg impossible pour %s: %s", video_path, e)

        return None

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path)
        self._current_wallpaper = str(p)
        self._is_paused = False

        target_file = str(p)
        media_type = MediaMetadataExtractor.get_media_type(p)

        if media_type == "video":
            logger.info("Vidéo sélectionnée en mode autonome : extraction d'une image haute résolution...")
            frame = self._extract_video_frame(p)
            if frame:
                target_file = str(frame)

        # Application effective selon l'environnement de bureau
        if self._gnome_engine.is_available():
            res = self._gnome_engine.apply(target_file, monitor=monitor, options=options)
            if res:
                logger.info("[MODE ADAPTATIF] Fond d'écran appliqué avec succès sur le bureau GNOME: %s", Path(target_file).name)
                return True

        if self._kde_engine.is_available():
            res = self._kde_engine.apply(target_file, monitor=monitor, options=options)
            if res:
                logger.info("[MODE ADAPTATIF] Fond d'écran appliqué avec succès sur le bureau KDE: %s", Path(target_file).name)
                return True

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
