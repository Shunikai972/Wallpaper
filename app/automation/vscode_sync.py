"""Synchronisation bidirectionnelle en temps réel entre le bureau et Visual Studio Code."""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.events import bus

logger = logging.getLogger("wallpapermaison.vscode_sync")

STATE_FILE = Path.home() / ".config/wallpapermaison/current_wallpaper.json"

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
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            ts = time.time()
            data = {
                "path": str(file_path),
                "media_type": media_type,
                "source": source,
                "timestamp": ts
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=2))

            perso_state = Path.home() / "reseau/Perso/.config/wallpapermaison/current_wallpaper.json"
            if perso_state.resolve() != STATE_FILE.resolve():
                try:
                    perso_state.parent.mkdir(parents=True, exist_ok=True)
                    with open(perso_state, "w", encoding="utf-8") as f:
                        f.write(json.dumps(data, indent=2))
                except Exception:
                    pass

            self._last_applied_timestamp = ts
            self._last_written_path = str(file_path)

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

    def _watch_loop(self) -> None:
        """Surveille le fichier current_wallpaper.json pour détecter les actions VS Code."""
        while not self._stop_event.is_set():
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
