"""Moteur de fond d'écran vidéo animé pour Linux GNOME (Wayland/Xwayland & X11).
Utilise une fenêtre Desktop GTK et MPV (natif ou via Flatpak) avec décodage matériel GPU.
"""

import logging
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import PROCESSED_DIR
from app.wallpaper.base import BaseWallpaperEngine
from app.wallpaper.engines.gnome_engine import GnomeWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.gtk_video")

class GtkVideoWallpaperEngine(BaseWallpaperEngine):
    """Affiche des vidéos animées en fond d'écran sur GNOME (Wayland/Xwayland) et X11."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._is_paused = False
        self._current_wallpaper: Optional[str] = None
        self._gnome_engine = GnomeWallpaperEngine()
        self._worker_script = Path(__file__).resolve().parent / "video_bg_worker.py"

    @property
    def name(self) -> str:
        return "gtk_video"

    @property
    def display_name(self) -> str:
        return "Lecteur Vidéo Arrière-Plan (GTK + MPV)"

    @property
    def supported_types(self) -> List[str]:
        return ["video", "gif"]

    def is_available(self) -> bool:
        # Nécessite un serveur d'affichage X11 ou Xwayland (standard sous GNOME Wayland)
        has_display = bool(os.environ.get("DISPLAY"))
        has_mpv = bool(shutil.which("mpv")) or self._has_mpv_player()
        return has_display and has_mpv

    @staticmethod
    def _has_mpv_player() -> bool:
        user_mpv = Path.home() / ".local" / "bin" / "mpv"
        if user_mpv.exists() and os.access(user_mpv, os.X_OK):
            return True
        if shutil.which("flatpak"):
            try:
                res = subprocess.run(
                    ["flatpak", "info", "io.mpv.Mpv"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return res.returncode == 0
            except Exception:
                pass
        return False

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            logger.error("Fichier vidéo introuvable: %s", p)
            return False

        self.stop()
        self._kill_all_existing_workers()
        options = options or {}
        fps = options.get("max_fps", 30)
        hwdec = "auto" if options.get("hw_decoding", True) else "no"

        # 1. Extraire et appliquer l'image fixe sous GNOME pour garder la cohérence
        self._apply_static_underlay(p, monitor, options)

        # 2. Lancer le worker d'arrière-plan vidéo
        python_exec = sys.executable
        cmd = [
            python_exec,
            str(self._worker_script),
            "--video", str(p),
            "--fps", str(fps),
            "--hwdec", hwdec
        ]

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )
            self._current_wallpaper = str(p)
            self._is_paused = False
            logger.info("Vidéo d'arrière-plan démarrée avec succès (PID %d) pour: %s", self._proc.pid, p.name)
            return True
        except Exception as e:
            logger.error("Erreur lors du démarrage du worker vidéo: %s", e)
            return False

    def _apply_static_underlay(self, video_path: Path, monitor: str, options: Optional[Dict[str, Any]]) -> None:
        """Applique une miniature haute résolution sur GNOME GSettings pour que le fond soit propre."""
        try:
            from app.media.thumbnail import thumbnail_generator
            thumb = thumbnail_generator.generate(video_path)
            if thumb and Path(thumb).exists() and self._gnome_engine.is_available():
                self._gnome_engine.apply(thumb, monitor=monitor, options=options)
        except Exception as e:
            logger.debug("Impossible d'appliquer l'image de fond statique: %s", e)

    def pause(self, monitor: str = "all") -> bool:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.send_signal(signal.SIGUSR1)
                self._is_paused = True
                logger.info("Vidéo d'arrière-plan mise en pause.")
                return True
            except Exception as e:
                logger.warning("Erreur pause vidéo: %s", e)
        return False

    def resume(self, monitor: str = "all") -> bool:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.send_signal(signal.SIGUSR2)
                self._is_paused = False
                logger.info("Vidéo d'arrière-plan reprise.")
                return True
            except Exception as e:
                logger.warning("Erreur reprise vidéo: %s", e)
        return False

    def stop(self, monitor: str = "all") -> bool:
        if self._proc:
            try:
                if self._proc.poll() is None:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                    else:
                        self._proc.terminate()
                    self._proc.wait(timeout=1.0)
                else:
                    self._proc.wait(timeout=0.2)
            except Exception:
                try:
                    self._proc.kill()
                    self._proc.wait(timeout=0.5)
                except Exception:
                    pass
            self._proc = None
        self._kill_all_existing_workers()
        self._current_wallpaper = None
        self._is_paused = False
        return True

    @staticmethod
    def _kill_all_existing_workers() -> None:
        try:
            subprocess.run(["pkill", "-9", "-f", "video_bg_worker.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            dirs_to_check = [Path("/tmp")]
            rdir = os.environ.get("XDG_RUNTIME_DIR")
            if rdir and os.path.isdir(rdir):
                dirs_to_check.append(Path(rdir))
            for d in dirs_to_check:
                for sock in d.glob("wallpapermaison_mpv*.sock"):
                    try:
                        sock.unlink()
                    except Exception:
                        pass
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        if self._proc and self._proc.poll() is not None:
            try:
                self._proc.wait(timeout=0.1)
            except Exception:
                pass
            self._proc = None
        is_running = bool(self._proc and self._proc.poll() is None)
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": self.is_available(),
            "supported_types": self.supported_types,
            "is_running": is_running,
            "is_paused": self._is_paused,
            "current_file": self._current_wallpaper if is_running else None
        }
