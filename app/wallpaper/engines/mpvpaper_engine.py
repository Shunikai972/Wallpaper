"""Moteur de fond d'écran vidéo/animé pour Wayland via mpvpaper."""

import logging
import os
import signal
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.mpvpaper")

class MpvpaperWallpaperEngine(BaseWallpaperEngine):
    """Gère l'affichage des fonds d'écran vidéo et GIF sous Wayland via mpvpaper."""

    def __init__(self) -> None:
        self._processes: Dict[str, subprocess.Popen] = {}
        self._current_file: Dict[str, str] = {}
        self._is_paused: bool = False

    @property
    def name(self) -> str:
        return "mpvpaper"

    @property
    def display_name(self) -> str:
        return "mpvpaper (Vidéos Wayland fluides)"

    @property
    def supported_types(self) -> List[str]:
        return ["video", "gif", "image"]

    def is_available(self) -> bool:
        has_bin = bool(shutil.which("mpvpaper"))
        is_wayland = os.environ.get("WAYLAND_DISPLAY") or "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        return bool(has_bin and is_wayland)

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False

        options = options or {}
        # Arrêt des processus existants pour ce moniteur ou globalement
        self.stop(monitor)

        target_output = "*" if monitor == "all" else monitor
        fps = options.get("max_fps", 30)
        hwdec = "auto" if options.get("hw_decoding", True) else "no"

        # Options mpv transmises
        mpv_opts = f"loop --hwdec={hwdec} --no-audio --framedrop=vo"
        if fps and fps < 60:
            mpv_opts += f" --override-display-fps={fps}"

        cmd = [
            "mpvpaper",
            "--auto-pause",
            "-o", mpv_opts,
            target_output,
            str(p)
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )
            self._processes[monitor] = proc
            self._current_file[monitor] = str(p)
            self._is_paused = False
            logger.info("mpvpaper lancé avec succès (PID %d, cible: %s, fichier: %s)", proc.pid, target_output, p.name)
            return True
        except Exception as e:
            logger.error("Impossible de lancer mpvpaper: %s", e)
            return False

    def pause(self, monitor: str = "all") -> bool:
        """Met en pause mpvpaper via signal SIGSTOP."""
        targets = list(self._processes.keys()) if monitor == "all" else [monitor]
        for t in targets:
            proc = self._processes.get(t)
            if proc and proc.poll() is None:
                try:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGSTOP)
                    else:
                        proc.send_signal(signal.SIGSTOP)
                except Exception as e:
                    logger.debug("Erreur pause mpvpaper: %s", e)
        self._is_paused = True
        logger.info("mpvpaper mis en pause.")
        return True

    def resume(self, monitor: str = "all") -> bool:
        """Reprend mpvpaper via signal SIGCONT."""
        targets = list(self._processes.keys()) if monitor == "all" else [monitor]
        for t in targets:
            proc = self._processes.get(t)
            if proc and proc.poll() is None:
                try:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGCONT)
                    else:
                        proc.send_signal(signal.SIGCONT)
                except Exception as e:
                    logger.debug("Erreur reprise mpvpaper: %s", e)
        self._is_paused = False
        logger.info("mpvpaper a repris la lecture.")
        return True

    def stop(self, monitor: str = "all") -> bool:
        targets = list(self._processes.keys()) if monitor == "all" else [monitor]
        for t in targets:
            proc = self._processes.get(t)
            if proc:
                try:
                    if proc.poll() is None:
                        if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        else:
                            proc.terminate()
                        proc.wait(timeout=1.0)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                self._processes.pop(t, None)
                self._current_file.pop(t, None)
        return True

    def get_status(self) -> Dict[str, Any]:
        running = any(p.poll() is None for p in self._processes.values())
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": self.is_available(),
            "supported_types": self.supported_types,
            "is_running": running,
            "is_paused": self._is_paused,
            "monitors": list(self._processes.keys())
        }
