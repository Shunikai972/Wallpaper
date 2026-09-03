"""Génération et mise en cache des miniatures haute performance."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image, ImageOps

from app.core.config import THUMBNAIL_DIR
from app.media.metadata import MediaMetadataExtractor

logger = logging.getLogger("wallpapermaison.thumbnail")

class ThumbnailGenerator:
    """Génère des miniatures 16:9 optimisées pour la bibliothèque."""
    def __init__(self, target_size: tuple = (480, 270)) -> None:
        self.target_size = target_size
        self.thumb_dir = THUMBNAIL_DIR
        self.thumb_dir.mkdir(parents=True, exist_ok=True)

    def get_thumbnail_path(self, file_path: Path, file_hash: Optional[str] = None) -> Path:
        """Retourne le chemin cible de la miniature basé sur le hash du fichier."""
        if not file_hash:
            file_hash = MediaMetadataExtractor.calculate_hash(file_path)
        if not file_hash:
            file_hash = f"h_{abs(hash(str(file_path)))}"
        return self.thumb_dir / f"{file_hash}.jpg"

    def generate(self, file_path: Path, file_hash: Optional[str] = None, force: bool = False) -> str:
        """Génère la miniature si nécessaire et retourne son chemin absolu."""
        if not file_path.exists():
            return ""

        thumb_path = self.get_thumbnail_path(file_path, file_hash)
        if thumb_path.exists() and not force:
            return str(thumb_path)

        media_type = MediaMetadataExtractor.get_media_type(file_path)

        try:
            if media_type == "video":
                success = self._generate_video_thumbnail(file_path, thumb_path)
            else:
                success = self._generate_image_thumbnail(file_path, thumb_path)
                if not success and shutil.which("ffmpeg"):
                    success = self._generate_video_thumbnail(file_path, thumb_path, is_video=False)

            if success and thumb_path.exists():
                return str(thumb_path)
        except Exception as e:
            logger.error("Échec de la génération de miniature pour %s: %s", file_path, e)

        return ""

    def _generate_image_thumbnail(self, src: Path, dest: Path) -> bool:
        try:
            with Image.open(src) as img:
                # Convertit en RGB si RGBA ou palette (pour format JPEG rapide et léger)
                if img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (20, 24, 34))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    img = bg
                else:
                    img = img.convert("RGB")

                # Recadre intelligemment en 16:9 centré
                thumb = ImageOps.fit(img, self.target_size, method=Image.Resampling.LANCZOS)
                thumb.save(dest, "JPEG", quality=82, optimize=True)
                return True
        except Exception as e:
            logger.debug("Erreur PIL thumbnail: %s", e)
            return False

    def _generate_video_thumbnail(self, src: Path, dest: Path, is_video: bool = True) -> bool:
        from app.media.media_tools import run_ffmpeg
        args = []
        if is_video:
            args += ["-ss", "00:00:01"]
        args += [
            "-i", str(src),
            "-vframes", "1",
            "-vf", f"scale={self.target_size[0]}:{self.target_size[1]}:force_original_aspect_ratio=increase,crop={self.target_size[0]}:{self.target_size[1]}",
            "-q:v", "3",
            "-y", str(dest)
        ]
        return run_ffmpeg(args, timeout=8)

thumbnail_generator = ThumbnailGenerator()
