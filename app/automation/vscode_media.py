"""Prepare media in a format and location the VS Code workbench can read."""

import hashlib
import fcntl
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("wallpapermaison.vscode_media")

VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg"}
TRANSCODE_PROFILE = "h264-1080p30-v1"


def _extension_root(configured_root: Optional[str] = None) -> Path:
    configured = configured_root or os.environ.get("WALLPAPERMAISON_VSCODE_EXT_DIR")
    if configured:
        root = Path(configured).expanduser()
    else:
        candidates = (
            Path("/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0"),
            Path.home() / ".vscode/extensions/budicuy.live-wallpaper-99.0.0",
            Path.home() / "reseau/Perso/.vscode/extensions/budicuy.live-wallpaper-99.0.0",
        )
        root = next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])
    root.mkdir(parents=True, exist_ok=True)
    return root


def _copy_atomically(source: Path, destination: Path) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=".wallpaper-",
            suffix=destination.suffix,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _transcode_h264(source: Path, destination: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg-full")
    if not ffmpeg:
        return False

    try:
        encoders = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Unable to inspect H.264 encoders in %s: %s", ffmpeg, exc)
        return False
    encoder = next(
        (candidate for candidate in ("libopenh264", "libx264") if candidate in encoders),
        None,
    )
    if not encoder:
        logger.warning("No compatible H.264 encoder is available in %s", ffmpeg)
        return False
    profile = "constrained_baseline" if encoder == "libopenh264" else "baseline"

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=".wallpaper-",
            suffix=".mp4",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-i",
                str(source),
                "-an",
                "-vf",
                "fps=30,scale=w='min(1920,iw)':h='min(1080,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                "-c:v",
                encoder,
                "-profile:v",
                profile,
                "-level:v",
                "4.1",
                "-b:v",
                "6M",
                "-maxrate",
                "8M",
                "-bufsize",
                "12M",
                "-g",
                "60",
                "-pix_fmt",
                "yuv420p",
                "-threads",
                "2",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            check=True,
        )
        if not temporary.is_file() or temporary.stat().st_size == 0:
            return False
        os.replace(temporary, destination)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        details = getattr(exc, "stderr", "")
        logger.warning("H.264 conversion failed for %s: %s %s", source, exc, details)
        return False
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def stage_media_for_vscode(media_path: str, extension_root: Optional[str] = None) -> str:
    """Stage media under the active extension root in a Chromium-compatible format."""
    source = Path(media_path).expanduser()
    try:
        source = source.resolve(strict=True)
        if not source.is_file():
            return str(source)

        media_dir = _extension_root(extension_root) / "wallpaper-media"
        media_dir.mkdir(parents=True, exist_ok=True)
        try:
            source.relative_to(media_dir.resolve())
            return str(source)
        except ValueError:
            pass

        stat = source.stat()
        transcode = source.suffix.lower() in VIDEO_EXTENSIONS
        profile = TRANSCODE_PROFILE if transcode else "copy-v1"
        identity = f"{profile}:{source}:{stat.st_size}:{stat.st_mtime_ns}"
        key = hashlib.sha256(identity.encode("utf-8", errors="surrogateescape")).hexdigest()[:20]
        extension = ".mp4" if transcode else source.suffix.lower()
        destination = media_dir / f"{key}{extension}"
        lock_path = media_dir / f".{key}.lock"
        with lock_path.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            if not destination.is_file() or destination.stat().st_size == 0:
                staged = _transcode_h264(source, destination) if transcode else False
                if not staged:
                    destination = media_dir / f"{key}{source.suffix.lower()}"
                    if not destination.is_file() or destination.stat().st_size != stat.st_size:
                        _copy_atomically(source, destination)

        staged_files = sorted(
            (item for item in media_dir.iterdir() if item.is_file() and not item.name.startswith(".")),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        )
        for stale in staged_files[8:]:
            try:
                stale.unlink()
            except OSError:
                pass
        return str(destination)
    except (OSError, ValueError) as exc:
        logger.warning("Unable to stage media for VS Code (%s): %s", media_path, exc)
        return str(source)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    if len(sys.argv) < 2:
        print("usage: stage_vscode_media.py MEDIA [EXTENSION_ROOT]", file=sys.stderr)
        raise SystemExit(2)
    staged_path = stage_media_for_vscode(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    if len(sys.argv) > 3 and sys.argv[3] == "--url":
        from app.automation.vscode_media_server import media_url_for

        print(media_url_for(staged_path))
    else:
        print(staged_path)
