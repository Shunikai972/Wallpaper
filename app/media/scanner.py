"""Scanner de dossiers asynchrone avec détection de médias et création de miniatures."""

import logging
import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from app.core.events import bus
from app.media.metadata import IMAGE_EXTENSIONS, ANIMATED_EXTENSIONS, VIDEO_EXTENSIONS, metadata_extractor
from app.media.thumbnail import thumbnail_generator
from app.storage.database import db

logger = logging.getLogger("wallpapermaison.scanner")

ALL_SUPPORTED_EXTS = IMAGE_EXTENSIONS | ANIMATED_EXTENSIONS | VIDEO_EXTENSIONS

class MediaScanner:
    """Scanne récursivement des dossiers de fonds d'écran de manière asynchrone."""
    def __init__(self) -> None:
        self._scanning = False
        self._abort = False
        self._current_thread: Optional[threading.Thread] = None
        self._state_lock = threading.Lock()

    def is_scanning(self) -> bool:
        with self._state_lock:
            return self._scanning

    def abort(self) -> None:
        with self._state_lock:
            self._abort = True

    def scan_directories_async(self, directories: List[str], recursive: bool = True,
                               on_progress: Optional[Callable[[int, int, str], None]] = None,
                               on_complete: Optional[Callable[[int], None]] = None) -> None:
        """Démarre le scan dans un thread en tâche de fond pour ne jamais bloquer l'UI."""
        def run() -> None:
            total_added = 0
            try:
                files_to_process: List[Path] = []
                for d_str in directories:
                    p = Path(d_str).expanduser()
                    if not p.exists():
                        continue
                    if p.is_file() and p.suffix.lower() in ALL_SUPPORTED_EXTS:
                        files_to_process.append(p)
                    elif p.is_dir():
                        pattern = "**/*" if recursive else "*"
                        for f in p.glob(pattern):
                            if self._abort:
                                break
                            if f.is_file() and f.suffix.lower() in ALL_SUPPORTED_EXTS:
                                files_to_process.append(f)

                total_files = len(files_to_process)
                logger.info("Début du scan: %d fichiers trouvés à indexer.", total_files)

                for idx, f in enumerate(files_to_process):
                    if self._abort:
                        logger.info("Scan interrompu par l'utilisateur.")
                        break

                    try:
                        # Notification d'avancement
                        if on_progress:
                            on_progress(idx + 1, total_files, f.name)
                        bus.emit("scan_progress", current=idx + 1, total=total_files, filename=f.name)

                        # Extraction métadonnées
                        meta = metadata_extractor.extract(f)

                        # Génération de miniature
                        thumb_path = thumbnail_generator.generate(f, meta.get("file_hash"))
                        meta["thumbnail_path"] = thumb_path

                        # Enregistrement en base de données
                        db.add_or_update_wallpaper(meta)
                        total_added += 1

                    except Exception as e:
                        logger.error("Erreur lors du traitement du fichier %s: %s", f, e)

                logger.info("Scan terminé. %d fichiers traités avec succès.", total_added)
                if on_complete:
                    on_complete(total_added)
                bus.emit("scan_complete", total_added=total_added)

            finally:
                with self._state_lock:
                    self._scanning = False
                    self._abort = False

        with self._state_lock:
            if self._scanning:
                logger.warning("Un scan est déjà en cours d'exécution.")
                return
            self._abort = False
            self._scanning = True
            self._current_thread = threading.Thread(
                target=run, daemon=True, name="MediaScannerThread"
            )
            self._current_thread.start()

    def scan_directories_sync(self, directories: List[str], recursive: bool = True) -> int:
        """Exécute le scan de manière synchrone en attendant la complétion (pour les commandes CLI)."""
        self.scan_directories_async(directories, recursive=recursive)
        with self._state_lock:
            current_thread = self._current_thread
        if current_thread:
            current_thread.join()
        return db.get_stats().get("total", 0)

    def import_single_file(self, file_path_str: str) -> Optional[Dict[str, Any]]:
        """Importe immédiatement un fichier individuel (ex. drag-and-drop dans l'interface)."""
        f = Path(file_path_str).expanduser()
        if not f.exists() or not f.is_file():
            return None
        if f.suffix.lower() not in ALL_SUPPORTED_EXTS:
            return None

        try:
            meta = metadata_extractor.extract(f)
            thumb_path = thumbnail_generator.generate(f, meta.get("file_hash"))
            meta["thumbnail_path"] = thumb_path
            wid = db.add_or_update_wallpaper(meta)
            logger.info("Fichier importé avec succès: %s (id: %s)", f.name, wid)
            return db.get_wallpaper_by_id(wid)
        except Exception as e:
            logger.error("Erreur import fichier unique %s: %s", f, e)
            return None

media_scanner = MediaScanner()
