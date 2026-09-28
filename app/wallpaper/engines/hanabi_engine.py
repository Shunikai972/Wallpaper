"""Moteur natif GNOME Shell via l'extension Hanabi."""

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.hanabi")


class HanabiWallpaperEngine(BaseWallpaperEngine):
    """Contrôle la vidéo de fond intégrée au compositeur GNOME via Hanabi."""

    SCHEMA = "io.github.jeffshee.hanabi-extension"
    UUID = "hanabi-extension@jeffshee.github.io"
    DBUS_DEST = "io.github.jeffshee.HanabiRenderer"
    DBUS_PATH = "/io/github/jeffshee/HanabiRenderer"
    DBUS_IFACE = "io.github.jeffshee.HanabiRenderer"

    def __init__(self) -> None:
        self._current_wallpaper: Optional[str] = None
        self._is_paused = False

    @property
    def name(self) -> str:
        return "hanabi"

    @property
    def display_name(self) -> str:
        return "GNOME Shell intégré (Hanabi)"

    @property
    def supported_types(self) -> List[str]:
        return ["video"]

    def is_available(self) -> bool:
        if not shutil.which("gsettings"):
            return False
        try:
            schema = subprocess.run(
                ["gsettings", "list-keys", self.SCHEMA],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            if schema.returncode != 0:
                return False

            extension_dirs = (
                Path.home() / ".local/share/gnome-shell/extensions" / self.UUID,
                Path.home() / "reseau/Perso/.local/share/gnome-shell/extensions" / self.UUID,
                Path("/usr/share/gnome-shell/extensions") / self.UUID,
            )
            if not any(path.is_dir() for path in extension_dirs):
                return False

            enabled = subprocess.run(
                ["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if enabled.returncode == 0 and self.UUID in enabled.stdout:
                return True

            info = shutil.which("gnome-extensions")
            if info:
                result = subprocess.run(
                    [info, "info", self.UUID],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                output = result.stdout.lower()
                return result.returncode == 0 and ("state: active" in output or "state: activ" in output)
        except (OSError, subprocess.SubprocessError):
            logger.debug("Impossible de vérifier l'extension Hanabi", exc_info=True)
        return False

    def _dbus_call(self, method: str, *arguments: str, timeout: float = 2.0) -> Optional[str]:
        """Appelle le renderer actif; None indique que le service n'est pas joignable."""
        gdbus = shutil.which("gdbus")
        if not gdbus:
            return None
        try:
            result = subprocess.run(
                [
                    gdbus,
                    "call",
                    "--session",
                    "--dest",
                    self.DBUS_DEST,
                    "--object-path",
                    self.DBUS_PATH,
                    "--method",
                    f"{self.DBUS_IFACE}.{method}",
                    *arguments,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.debug("Commande Hanabi %s indisponible: %s", method, exc)
            return None
        if result.returncode != 0:
            logger.debug("Hanabi %s: %s", method, result.stderr.strip())
            return None
        return result.stdout.strip()

    def _renderer_is_playing(self) -> Optional[bool]:
        gdbus = shutil.which("gdbus")
        if not gdbus:
            return None
        try:
            result = subprocess.run(
                [
                    gdbus,
                    "call",
                    "--session",
                    "--dest",
                    self.DBUS_DEST,
                    "--object-path",
                    self.DBUS_PATH,
                    "--method",
                    "org.freedesktop.DBus.Properties.Get",
                    self.DBUS_IFACE,
                    "isPlaying",
                ],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        value = result.stdout.lower()
        if "true" in value:
            return True
        if "false" in value:
            return False
        return None

    def _renderer_playback_position(self) -> Optional[float]:
        """Return Hanabi's media clock in seconds when supported by its renderer."""
        value = self._dbus_call("getPlaybackPosition", timeout=1.5)
        if value is None:
            return None
        try:
            return float(value.strip().strip("(),"))
        except ValueError:
            return None

    def _set_video_path(self, playable_path: str) -> bool:
        """Synchronise GSettings and the live renderer, which may start after login."""
        settings_ok = False
        commands = [["gsettings", "set", self.SCHEMA, "video-path", playable_path]]
        for schema_dir in (
            Path.home() / ".local/share/gnome-shell/extensions" / self.UUID / "schemas",
            Path.home() / "reseau/Perso/.local/share/gnome-shell/extensions" / self.UUID / "schemas",
        ):
            if schema_dir.is_dir():
                commands.append(
                    ["gsettings", "--schemadir", str(schema_dir), "set", self.SCHEMA, "video-path", playable_path]
                )

        for command in commands:
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    settings_ok = True
                    break
            except (OSError, subprocess.SubprocessError):
                continue
        if not settings_ok:
            logger.error("Impossible d'enregistrer le chemin vidéo Hanabi: %s", playable_path)
            return False

        # À la connexion, systemd/XDG Autostart peut démarrer avant le renderer.
        # Attendre son bus évite de considérer une simple écriture GSettings comme une lecture.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self._dbus_call("setFilePath", playable_path, timeout=1.5) is not None:
                self._dbus_call("setPlay", timeout=1.5)
                break
            time.sleep(0.25)
        else:
            logger.error("Le renderer Hanabi n'est pas disponible dans cette session graphique.")
            return False

        playback_deadline = time.monotonic() + 8
        last_position: Optional[float] = None
        while time.monotonic() < playback_deadline:
            playing = self._renderer_is_playing()
            position = self._renderer_playback_position()
            if position is not None and position >= 0:
                if last_position is not None and abs(position - last_position) >= 0.05:
                    return True
                last_position = position
            elif playing is True:
                # Compatibility with Hanabi versions that do not expose a media clock.
                return True
            time.sleep(0.25)

        if last_position is not None:
            logger.error("Hanabi ne fait pas avancer la vidéo %s (position finale: %.3fs).", playable_path, last_position)
        else:
            logger.error("Hanabi n'a pas démarré la lecture de %s.", playable_path)
        return False

    def apply(
        self,
        wallpaper_path: str,
        monitor: str = "all",
        options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        source = Path(wallpaper_path).expanduser().resolve()
        if not source.is_file():
            logger.error("Vidéo de fond introuvable: %s", source)
            return False

        try:
            from app.wallpaper.video_optimizer import video_optimizer

            playable_path = str(Path(video_optimizer.get_playable_path(str(source))).expanduser().resolve())
            if not Path(playable_path).is_file():
                logger.error("Version vidéo lisible introuvable: %s", playable_path)
                return False

            extension_ctl = shutil.which("gnome-extensions")
            if extension_ctl:
                subprocess.run(
                    [extension_ctl, "enable", self.UUID],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                )

            if not self._set_video_path(playable_path):
                return False

            self._current_wallpaper = str(source)
            self._is_paused = False
            logger.info("Lecture confirmée par Hanabi: %s", source.name)
            return True
        except (OSError, subprocess.SubprocessError, Exception) as exc:
            logger.error("Erreur lors de l'application via Hanabi: %s", exc)
            return False

    def pause(self, monitor: str = "all") -> bool:
        result = self._dbus_call("setPause")
        self._is_paused = result is not None
        return self._is_paused

    def resume(self, monitor: str = "all") -> bool:
        result = self._dbus_call("setPlay")
        self._is_paused = result is None
        return result is not None

    def stop(self, monitor: str = "all") -> bool:
        self._dbus_call("setPause")
        try:
            subprocess.run(
                ["gsettings", "set", self.SCHEMA, "video-path", ""],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
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
            "is_running": self._renderer_is_playing() is True,
            "is_paused": self._is_paused,
            "current_file": self._current_wallpaper,
        }
