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
    user_mpv = Path.home() / ".local" / "bin" / "mpv"
    if user_mpv.exists() and os.access(user_mpv, os.X_OK):
        return [str(user_mpv)]
    if shutil.which("flatpak"):
        try:
            res = subprocess.run(["flatpak", "info", "io.mpv.Mpv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return ["flatpak", "run", "--filesystem=host", "io.mpv.Mpv"]
        except Exception:
            pass
    return ["mpv"]

def get_media_env() -> Dict[str, str]:
    """Retourne l'environnement d'exécution avec les bibliothèques de codecs (OpenH264)."""
    env = dict(os.environ)
    home = Path.home()
    extra_dirs = [
        str(home / ".local/lib"),
        str(home / "reseau/Perso/.local/lib"),
        str(Path(__file__).resolve().parents[2] / "gnome-extension/hanabi-extension@jeffshee.github.io/lib"),
    ]
    valid_dirs = [d for d in extra_dirs if os.path.isdir(d)]
    if valid_dirs:
        current_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(valid_dirs) + (f":{current_ld}" if current_ld else "")
    return env

def run_ffmpeg(cmd_args: List[str], timeout: int = 10) -> bool:
    """Exécute ffmpeg avec repli automatique sur le flatpak MPV officiel si le ffmpeg système manque de codecs."""
    # 1. Tentative native
    if shutil.which("ffmpeg"):
        try:
            res = subprocess.run(
                ["ffmpeg"] + cmd_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                env=get_media_env()
            )
            if res.returncode == 0:
                return True
            logger.debug("ffmpeg système a échoué (code %d) : tentative avec flatpak codecs", res.returncode)
        except Exception as e:
            logger.debug("Erreur exécution ffmpeg système: %s", e)

    # 2. Tentative via Flatpak MPV
    if shutil.which("flatpak"):
        try:
            cmd = ["flatpak", "run", "--filesystem=host", "--command=ffmpeg", "io.mpv.Mpv"] + cmd_args
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
            if res.returncode == 0:
                return True
        except Exception as e:
            logger.debug("Erreur exécution ffmpeg flatpak: %s", e)

    return False

def run_ffprobe_json(file_path: Path, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Exécute ffprobe pour analyser les métadonnées avec repli sur le lecteur Flatpak MPV."""
    common_args = ["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]

    # 1. Tentative native
    if shutil.which("ffprobe"):
        try:
            out = subprocess.check_output(
                ["ffprobe"] + common_args,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
                env=get_media_env()
            )
            data = json.loads(out)
            if data and ("format" in data or "streams" in data):
                return data
        except Exception:
            pass

    # 2. Tentative Flatpak MPV
    if shutil.which("flatpak"):
        try:
            cmd = ["flatpak", "run", "--filesystem=host", "--command=ffprobe", "io.mpv.Mpv"] + common_args
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=timeout)
            idx = out.find("{")
            if idx != -1:
                return json.loads(out[idx:])
        except Exception as e:
            logger.debug("Erreur ffprobe flatpak pour %s: %s", file_path, e)

    return None
