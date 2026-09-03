"""Détection d'applications plein écran, de jeux et du verrouillage d'écran sous Linux."""

import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Set, Optional

from app.core.events import bus

logger = logging.getLogger("wallpapermaison.window_monitor")

# Processus fréquents de jeux ou logiciels plein écran intensifs
KNOWN_GAME_PROCESSES: Set[str] = {
    "steam", "steamwebhelper", "gamescope", "wine", "wine64", "wineserver",
    "proton", "lutris", "heroic", "retroarch", "dota2", "cs2", "hl2_linux",
    "minecraft", "vlc", "obs64", "blender"
}

class WindowMonitor:
    """Surveille les applications en plein écran et le verrouillage de session."""
    def __init__(self, check_interval: float = 3.0) -> None:
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_fullscreen = False
        self._is_locked = False

    def is_fullscreen_active(self) -> bool:
        """Indique si une application plein écran ou un jeu est actif."""
        # 1. Vérification X11 si xprop est disponible
        if shutil.which("xprop") and os.environ.get("DISPLAY"):
            try:
                out = subprocess.check_output(
                    ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                    stderr=subprocess.DEVNULL, text=True, timeout=1
                )
                if "_NET_ACTIVE_WINDOW(WINDOW)" in out:
                    win_id = out.split("#")[-1].strip()
                    if win_id and win_id != "0x0":
                        state_out = subprocess.check_output(
                            ["xprop", "-id", win_id, "_NET_WM_STATE"],
                            stderr=subprocess.DEVNULL, text=True, timeout=1
                        )
                        if "_NET_WM_STATE_FULLSCREEN" in state_out:
                            return True
            except Exception:
                pass

        # 2. Vérification des processus actifs (jeux / logiciels lourds)
        if self._check_game_processes():
            return True

        return False

    def _check_game_processes(self) -> bool:
        """Scanne /proc pour identifier si un jeu ou processus lourd est en cours."""
        try:
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                comm_file = os.path.join("/proc", pid, "comm")
                if os.path.isfile(comm_file):
                    with open(comm_file, "r") as f:
                        name = f.read().strip().lower()
                        if name in KNOWN_GAME_PROCESSES:
                            return True
        except Exception:
            pass
        return False

    def is_session_locked(self) -> bool:
        """Vérifie si la session est verrouillée via DBus ScreenSaver."""
        if shutil.which("gdbus"):
            try:
                out = subprocess.check_output([
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.ScreenSaver",
                    "--object-path", "/org/gnome/ScreenSaver",
                    "--method", "org.gnome.ScreenSaver.GetActive"
                ], stderr=subprocess.DEVNULL, text=True, timeout=1)
                return "(true,)" in out.lower() or "true" in out.lower()
            except Exception:
                pass

            try:
                out = subprocess.check_output([
                    "gdbus", "call", "--session",
                    "--dest", "org.freedesktop.ScreenSaver",
                    "--object-path", "/org/freedesktop/ScreenSaver",
                    "--method", "org.freedesktop.ScreenSaver.GetActive"
                ], stderr=subprocess.DEVNULL, text=True, timeout=1)
                return "(true,)" in out.lower() or "true" in out.lower()
            except Exception:
                pass

        return False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="WindowMonitorThread")
        self._thread.start()
        logger.info("Surveillance des fenêtres et du plein écran démarrée.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Surveillance des fenêtres arrêtée.")

    def _poll_loop(self) -> None:
        while self._running:
            try:
                fs = self.is_fullscreen_active()
                if fs != self._is_fullscreen:
                    self._is_fullscreen = fs
                    logger.info("Changement d'état plein écran: %s", fs)
                    bus.emit("fullscreen_state_changed", is_fullscreen=fs)

                locked = self.is_session_locked()
                if locked != self._is_locked:
                    self._is_locked = locked
                    logger.info("Changement d'état verrouillage écran: %s", locked)
                    bus.emit("screen_locked", is_locked=locked)
            except Exception as e:
                logger.debug("Erreur polling window_monitor: %s", e)
            time.sleep(self.check_interval)

window_monitor = WindowMonitor()
