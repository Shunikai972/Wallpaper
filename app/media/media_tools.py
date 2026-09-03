"""Outils multimédias adaptatifs (FFmpeg, FFprobe, MPV).
Bascule automatiquement sur le moteur Flatpak avec codecs complets (H264/HEVC) si les outils système sont incomplets.
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger("wallpapermaison.media_tools")

def get_mpv_command() -> List[str]:
    """Retourne la commande optimale pour lancer MPV."""
    if shutil.which("mpv"):
        return ["mpv"]
    if shutil.which("flatpak"):
        return ["flatpak", "run", "--filesystem=host", "--command=mpv", "io.github.celluloid_player.Celluloid"]
    return ["mpv"]

def run_ffmpeg(cmd_args: List[str], timeout: int = 10) -> bool:
    """Exécute ffmpeg avec repli automatique sur le flatpak Celluloid si le ffmpeg système manque de codecs."""
    # 1. Tentative native
    if shutil.which("ffmpeg"):
        try:
            res = subprocess.run(
                ["ffmpeg"] + cmd_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False
            )
            if res.returncode == 0:
                return True
            logger.debug("ffmpeg système a échoué (code %d) : tentative avec flatpak codecs", res.returncode)
        except Exception as e:
            logger.debug("Erreur exécution ffmpeg système: %s", e)

    # 2. Tentative via Flatpak
    if shutil.which("flatpak"):
        try:
            cmd = ["flatpak", "run", "--filesystem=host", "--command=ffmpeg", "io.github.celluloid_player.Celluloid"] + cmd_args
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
            if res.returncode == 0:
                return True
        except Exception as e:
            logger.debug("Erreur exécution ffmpeg flatpak: %s", e)

    return False

def run_ffprobe_json(file_path: Path, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Exécute ffprobe pour analyser les métadonnées avec repli sur le lecteur Flatpak."""
    common_args = ["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]

    # 1. Tentative native
    if shutil.which("ffprobe"):
        try:
            out = subprocess.check_output(["ffprobe"] + common_args, stderr=subprocess.DEVNULL, text=True, timeout=timeout)
            data = json.loads(out)
            if data and ("format" in data or "streams" in data):
                return data
        except Exception:
            pass

    # 2. Tentative Flatpak
    if shutil.which("flatpak"):
        try:
            cmd = ["flatpak", "run", "--filesystem=host", "--command=ffprobe", "io.github.celluloid_player.Celluloid"] + common_args
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=timeout)
            # Nettoyage des éventuels messages flatpak sur stdout avant le JSON
            idx = out.find("{")
            if idx != -1:
                return json.loads(out[idx:])
        except Exception as e:
            logger.debug("Erreur ffprobe flatpak pour %s: %s", file_path, e)

    return None
