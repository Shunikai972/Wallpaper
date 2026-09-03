"""Extraction robuste de métadonnées pour images, GIFs animés et vidéos."""

import hashlib
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image

logger = logging.getLogger("wallpapermaison.metadata")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif", ".jxl", ".svg"}
ANIMATED_EXTENSIONS = {".gif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".flv", ".m4v"}

class MediaMetadataExtractor:
    """Extrait les dimensions, type, durée et fps d'un fichier média."""

    @staticmethod
    def get_media_type(file_path: Path) -> str:
        """Détermine le type de média d'après l'extension et le contenu."""
        ext = file_path.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return "video"
        if ext in ANIMATED_EXTENSIONS:
            return "gif"
        if ext in IMAGE_EXTENSIONS:
            # Vérification si WEBP animé
            if ext == ".webp":
                try:
                    with Image.open(file_path) as img:
                        if getattr(img, "is_animated", False) and img.n_frames > 1:
                            return "gif"
                except Exception:
                    pass
            return "image"
        return "unknown"

    @classmethod
    def extract(cls, file_path: Path) -> Dict[str, Any]:
        """Extrait toutes les métadonnées utiles du fichier."""
        media_type = cls.get_media_type(file_path)
        stat = file_path.stat()
        file_size = stat.st_size

        info: Dict[str, Any] = {
            "file_path": str(file_path.resolve()),
            "file_name": file_path.name,
            "file_size": file_size,
            "media_type": media_type,
            "width": 0,
            "height": 0,
            "duration": 0.0,
            "fps": 0.0,
            "file_hash": cls.calculate_hash(file_path)
        }

        if media_type == "video":
            cls._extract_video_metadata(file_path, info)
        elif media_type in ["image", "gif"]:
            cls._extract_image_metadata(file_path, info)

        return info

    @classmethod
    def _extract_image_metadata(cls, file_path: Path, info: Dict[str, Any]) -> None:
        try:
            with Image.open(file_path) as img:
                info["width"] = img.width
                info["height"] = img.height

                if getattr(img, "is_animated", False):
                    info["media_type"] = "gif"
                    n_frames = getattr(img, "n_frames", 1)
                    duration_per_frame = img.info.get("duration", 100) # millisecondes
                    total_duration = (n_frames * duration_per_frame) / 1000.0
                    info["duration"] = round(total_duration, 2)
                    if duration_per_frame > 0:
                        info["fps"] = round(1000.0 / duration_per_frame, 1)
        except Exception as e:
            if shutil.which("ffprobe"):
                cls._extract_video_metadata(file_path, info)
                if info["width"] > 0 and info["height"] > 0:
                    return
            info["width"] = 1920
            info["height"] = 1080
            logger.debug("Métadonnées estimées pour %s: %s", file_path, e)

    @classmethod
    def _extract_video_metadata(cls, file_path: Path, info: Dict[str, Any]) -> None:
        from app.media.media_tools import run_ffprobe_json
        data = run_ffprobe_json(file_path, timeout=6)
        if data:
            try:
                fmt = data.get("format", {})
                info["duration"] = round(float(fmt.get("duration", 0.0)), 2)

                for s in data.get("streams", []):
                    if s.get("codec_type") == "video":
                        info["width"] = int(s.get("width", 0))
                        info["height"] = int(s.get("height", 0))
                        r_frame = s.get("r_frame_rate", "0/0")
                        if "/" in r_frame:
                            num, den = r_frame.split("/")
                            if float(den) > 0:
                                info["fps"] = round(float(num) / float(den), 1)
                        break
                return
            except Exception as e:
                logger.debug("Parsing ffprobe data a échoué pour %s: %s", file_path, e)

        # Fallback par défaut
        info["width"] = 1920
        info["height"] = 1080
        info["duration"] = 0.0
        info["fps"] = 30.0

    @staticmethod
    def calculate_hash(file_path: Path, max_bytes: int = 1024 * 1024) -> str:
        """Calcule un hash rapide basé sur le début et la fin du fichier + sa taille."""
        try:
            hasher = hashlib.md5()
            hasher.update(str(file_path.stat().st_size).encode("utf-8"))
            with open(file_path, "rb") as f:
                head = f.read(max_bytes // 2)
                hasher.update(head)
                if file_path.stat().st_size > max_bytes:
                    f.seek(-max_bytes // 2, os.SEEK_END)
                    tail = f.read(max_bytes // 2)
                    hasher.update(tail)
            return hasher.hexdigest()
        except Exception:
            return ""

metadata_extractor = MediaMetadataExtractor()
