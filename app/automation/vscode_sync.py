"""Synchronisation bidirectionnelle en temps réel entre le bureau et Visual Studio Code."""

import ast
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.events import bus
from app.automation.vscode_media import stage_media_for_vscode
from app.automation.vscode_media_server import media_url_for

logger = logging.getLogger("wallpapermaison.vscode_sync")

STATE_FILE = Path.home() / ".config/wallpapermaison/current_wallpaper.json"


def _atomic_write_text(target: Path, content: str) -> None:
    """Publish complete state snapshots to concurrent readers."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


class VsCodeSync:
    """Gestionnaire de synchronisation bidirectionnelle Desktop <-> VS Code."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_applied_timestamp: float = 0.0
        self._last_written_path: str = ""
        self._is_applying_from_vscode = False

        # Abonnement aux événements de changement de fond d'écran sur le bureau
        bus.subscribe("wallpaper_changed", self._on_desktop_wallpaper_changed)

    def start(self) -> None:
        """Démarre le thread de surveillance des changements venant de VS Code."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._watch_loop, name="VsCodeSyncThread", daemon=True)
        self._thread.start()
        logger.info("Service de synchronisation bidirectionnelle VS Code démarré.")

    def stop(self) -> None:
        """Arrête le service de synchronisation."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Service de synchronisation VS Code arrêté.")

    def _on_desktop_wallpaper_changed(self, wallpaper: Dict[str, Any], monitor: str = "all", engine: str = "") -> None:
        """Appelé lors d'un changement de fond d'écran sur le bureau."""
        if self._is_applying_from_vscode:
            return

        file_path = wallpaper.get("file_path", "")
        media_type = wallpaper.get("media_type", "image")
        if not file_path or not os.path.exists(file_path):
            return

        self.publish_state(file_path=file_path, media_type=media_type, source="desktop")

    def publish_state(self, file_path: str, media_type: str = "video", source: str = "desktop") -> None:
        """Écrit l'état partagé et met à jour workbench.html et le lien symbolique."""
        try:
            vscode_media_path = stage_media_for_vscode(file_path)
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            ts = time.time()
            data = {
                "path": str(file_path),
                "media_type": media_type,
                "source": source,
                "timestamp": ts
            }
            state_json = json.dumps(data, indent=2)
            _atomic_write_text(STATE_FILE, state_json)

            perso_state = Path.home() / "reseau/Perso/.config/wallpapermaison/current_wallpaper.json"
            if perso_state.resolve() != STATE_FILE.resolve():
                try:
                    perso_state.parent.mkdir(parents=True, exist_ok=True)
                    _atomic_write_text(perso_state, state_json)
                except Exception:
                    pass

            self._last_applied_timestamp = ts
            self._last_written_path = str(file_path)

            # Écriture instantanée des fichiers live_state pour mise à jour à chaud de VS Code sans reload
            vscode_media_url = media_url_for(vscode_media_path)
            live_json_data = json.dumps({"path": vscode_media_url, "media_type": media_type, "timestamp": ts}, indent=2)
            live_js_code = f""";(function() {{
    var p = {json.dumps(vscode_media_url, ensure_ascii=True)};
    if (typeof window.__applyWallpaperMaisonMedia === 'function') {{
        window.__applyWallpaperMaisonMedia(p);
    }}
}})();\n"""
            for target_dir in [
                Path("/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0"),
                Path.home() / ".vscode/extensions/budicuy.live-wallpaper-99.0.0",
                Path.home() / "reseau/Perso/.vscode/extensions/budicuy.live-wallpaper-99.0.0",
                Path.home() / ".config/wallpapermaison",
                Path.home() / "reseau/Perso/.config/wallpapermaison"
            ]:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    _atomic_write_text(target_dir / "live_state.json", live_json_data)
                    _atomic_write_text(target_dir / "live_state.js", live_js_code)
                except Exception:
                    pass

            # Mise à jour du lien symbolique de téléchargement
            if media_type == "video":
                for dl_candidate in [
                    Path.home() / "reseau/Perso/Téléchargements",
                    Path.home() / "Téléchargements",
                    Path.home() / "Downloads"
                ]:
                    if dl_candidate.exists():
                        link = dl_candidate / "wallpaper.mp4"
                        try:
                            if link.is_symlink() or link.exists():
                                link.unlink()
                            link.symlink_to(file_path)
                        except Exception:
                            pass
                        break

            # Patch statique workbench.html pour persistance au démarrage
            patch_script = Path(__file__).resolve().parents[2] / "scripts/patch_vscode_html.py"
            if patch_script.exists():
                subprocess.run([sys.executable, str(patch_script), str(file_path)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

            logger.debug("État partagé VS Code publié: %s (source: %s)", file_path, source)

        except Exception as e:
            logger.error("Erreur écriture état partagé VS Code: %s", e)

    def _get_hanabi_video_path(self) -> Optional[str]:
        """Récupère le chemin vidéo actuellement configuré dans Hanabi GNOME Shell."""
        import shutil
        if shutil.which("gdbus"):
            try:
                result = subprocess.run(
                    [
                        "gdbus", "call", "--session", "--dest", "io.github.jeffshee.HanabiRenderer",
                        "--object-path", "/io/github/jeffshee/HanabiRenderer",
                        "--method", "io.github.jeffshee.HanabiRenderer.getFilePath",
                    ],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1,
                )
                if result.returncode == 0:
                    reply = ast.literal_eval(result.stdout.strip())
                    active_path = reply[0] if isinstance(reply, tuple) and reply else ""
                    if active_path and os.path.exists(active_path):
                        return active_path
            except (OSError, SyntaxError, ValueError, subprocess.SubprocessError):
                pass

        if not shutil.which("gsettings"):
            return None
        # GSettings fallback for older renderer versions.
        try:
            res = subprocess.run(
                ["gsettings", "get", "io.github.jeffshee.hanabi-extension", "video-path"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1
            )
            if res.returncode == 0:
                val = res.stdout.strip().strip("'\"")
                if val and os.path.exists(val):
                    return val
        except Exception:
            pass
        # Essai avec --schemadir
        for s_dir in [
            Path.home() / ".local/share/gnome-shell/extensions/hanabi-extension@jeffshee.github.io/schemas",
            Path.home() / "reseau/Perso/.local/share/gnome-shell/extensions/hanabi-extension@jeffshee.github.io/schemas"
        ]:
            if s_dir.exists():
                try:
                    res = subprocess.run(
                        ["gsettings", "--schemadir", str(s_dir), "get", "io.github.jeffshee.hanabi-extension", "video-path"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1
                    )
                    if res.returncode == 0:
                        val = res.stdout.strip().strip("'\"")
                        if val and os.path.exists(val):
                            return val
                except Exception:
                    pass
        return None

    def _watch_loop(self) -> None:
        """Surveille le fichier current_wallpaper.json et GSettings Hanabi pour synchronisation temps réel."""
        while not self._stop_event.is_set():
            # 1. Vérification si Hanabi a changé de wallpaper directement sur le bureau
            try:
                hanabi_val = self._get_hanabi_video_path()
                if hanabi_val:
                    try:
                        same_path = os.path.realpath(hanabi_val) == os.path.realpath(self._last_written_path)
                    except (OSError, TypeError):
                        same_path = os.path.abspath(hanabi_val) == os.path.abspath(self._last_written_path)
                    if not same_path:
                        logger.info("Changement de fond d'écran détecté depuis Hanabi bureau : %s", hanabi_val)
                        self.publish_state(hanabi_val, media_type="video", source="desktop")
            except Exception as e:
                logger.debug("Erreur surveillance GSettings Hanabi: %s", e)

            # 2. Surveillance du fichier d'état partagé current_wallpaper.json
            try:
                if STATE_FILE.exists():
                    content = STATE_FILE.read_text(encoding="utf-8")
                    data = json.loads(content)
                    source = data.get("source", "")
                    ts = float(data.get("timestamp", 0))
                    file_path = data.get("path", "")

                    if source == "vscode" and ts > self._last_applied_timestamp:
                        self._last_applied_timestamp = ts
                        if file_path and os.path.exists(file_path):
                            logger.info("Changement de wallpaper initié depuis VS Code : %s", file_path)
                            self._is_applying_from_vscode = True
                            self._last_written_path = file_path
                            try:
                                from app.wallpaper.manager import wallpaper_manager
                                wallpaper_manager.apply_wallpaper_by_path(file_path)
                            finally:
                                self._is_applying_from_vscode = False
            except Exception as e:
                logger.debug("Erreur surveillance état VS Code: %s", e)

            # Pause ultra-courte de surveillance (réactivité ~200ms)
            for _ in range(4):
                if self._stop_event.is_set():
                    break
                time.sleep(0.05)

vscode_sync = VsCodeSync()
