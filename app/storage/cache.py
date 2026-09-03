"""Gestionnaire de cache pour les miniatures et images traitées."""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any

from app.core.config import THUMBNAIL_DIR, PROCESSED_DIR, config_manager

logger = logging.getLogger("wallpapermaison.cache")

class CacheManager:
    """Gestionnaire de cache sur disque."""
    def __init__(self) -> None:
        self.thumbnail_dir = THUMBNAIL_DIR
        self.processed_dir = PROCESSED_DIR
        self.ensure_dirs()

    def ensure_dirs(self) -> None:
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Calcule la taille actuelle du cache et le nombre de fichiers."""
        thumb_size = 0
        thumb_count = 0
        for p in self.thumbnail_dir.glob("*"):
            if p.is_file():
                thumb_size += p.stat().st_size
                thumb_count += 1

        proc_size = 0
        proc_count = 0
        for p in self.processed_dir.glob("*"):
            if p.is_file():
                proc_size += p.stat().st_size
                proc_count += 1

        total_size = thumb_size + proc_size
        max_size_mb = config_manager.get("cache_max_size_mb", 2048)
        max_size_bytes = max_size_mb * 1024 * 1024

        return {
            "total_bytes": total_size,
            "total_mb": round(total_size / (1024 * 1024), 2),
            "max_mb": max_size_mb,
            "percentage": min(100.0, round((total_size / max_size_bytes) * 100, 1)) if max_size_bytes > 0 else 0,
            "thumbnail_files": thumb_count,
            "processed_files": proc_count
        }

    def clear_cache(self, clear_thumbnails: bool = True, clear_processed: bool = True) -> Dict[str, Any]:
        """Nettoie le contenu du cache sélectionné."""
        freed_bytes = 0
        if clear_thumbnails and self.thumbnail_dir.exists():
            for item in self.thumbnail_dir.iterdir():
                try:
                    if item.is_file():
                        freed_bytes += item.stat().st_size
                        item.unlink()
                except Exception as e:
                    logger.warning("Impossible de supprimer %s: %s", item, e)

        if clear_processed and self.processed_dir.exists():
            for item in self.processed_dir.iterdir():
                try:
                    if item.is_file():
                        freed_bytes += item.stat().st_size
                        item.unlink()
                except Exception as e:
                    logger.warning("Impossible de supprimer %s: %s", item, e)

        logger.info("Cache vidé. Espace libéré: %.2f MB", freed_bytes / (1024 * 1024))
        return {
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2)
        }

    def enforce_size_limit(self) -> None:
        """Supprime les fichiers les plus anciens si la taille max est dépassée."""
        stats = self.get_cache_stats()
        max_bytes = stats["max_mb"] * 1024 * 1024
        if stats["total_bytes"] <= max_bytes:
            return

        # Liste tous les fichiers triés par date de dernier accès
        files = []
        for d in [self.processed_dir, self.thumbnail_dir]:
            for p in d.glob("*"):
                if p.is_file():
                    files.append((p.stat().st_atime, p.stat().st_size, p))

        files.sort(key=lambda x: x[0]) # Les plus anciens en premier
        current_size = stats["total_bytes"]

        for _, size, path in files:
            if current_size <= max_bytes * 0.8: # On libère jusqu'à 80% du quota
                break
            try:
                path.unlink()
                current_size -= size
            except Exception:
                pass

cache_manager = CacheManager()
