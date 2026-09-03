"""Moteur de fond d'écran vidéo sous X11 via xwinwrap + mpv."""

import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.xwinwrap")

class XwinwrapWallpaperEngine(BaseWallpaperEngine):
    """Affiche des vidéos en fond d'écran sur le root window X11."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._is_paused = False

    @property
    def name(self) -> str:
        return "xwinwrap"

    @property
    def display_name(self) -> str:
        return "xwinwrap + mpv (Vidéos X11)"

    @property
    def supported_types(self) -> List[str]:
        return ["video", "gif"]

    def is_available(self) -> bool:
        has_tools = bool(shutil.which("xwinwrap") and shutil.which("mpv"))
        is_x11 = bool(os.environ.get("DISPLAY")) and "wayland" not in os.environ.get("XDG_SESSION_TYPE", "").lower()
        return bool(has_tools and is_x11)

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False

        self.stop()
        options = options or {}
        hwdec = "auto" if options.get("hw_decoding", True) else "no"
        fps = options.get("max_fps", 30)

        cmd = [
            "xwinwrap", "-fs", "-fdt", "-ni", "-b", "-nf", "--",
            "mpv", "-wid", "WID",
            "--loop", "--no-audio",
            f"--hwdec={hwdec}",
            f"--override-display-fps={fps}",
            str(p)
        ]

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )
            self._is_paused = False
            logger.info("xwinwrap + mpv lancé (PID %d) pour %s", self._proc.pid, p.name)
            return True
        except Exception as e:
            logger.error("Erreur lancement xwinwrap: %s", e)
            return False

    def pause(self, monitor: str = "all") -> bool:
        if self._proc and self._proc.poll() is None:
            try:
                if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGSTOP)
                else:
                    self._proc.send_signal(signal.SIGSTOP)
                self._is_paused = True
                return True
            except Exception:
                pass
        return False

    def resume(self, monitor: str = "all") -> bool:
        if self._proc and self._proc.poll() is None:
            try:
                if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGCONT)
                else:
                    self._proc.send_signal(signal.SIGCONT)
                self._is_paused = False
                return True
            except Exception:
                pass
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
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": self.is_available(),
            "supported_types": self.supported_types,
            "is_running": bool(self._proc and self._proc.poll() is None),
            "is_paused": self._is_paused
        }
