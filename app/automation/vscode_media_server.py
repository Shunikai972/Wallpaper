"""Serve staged wallpaper files to Electron with correct MIME and byte ranges."""

import fcntl
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import ProxyHandler, build_opener

EXTENSION_ROOT = Path(
    os.environ.get(
        "WALLPAPERMAISON_VSCODE_EXT_DIR",
        "/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0",
    )
).expanduser()
MEDIA_ROOT = Path(
    os.environ.get("WALLPAPERMAISON_VSCODE_MEDIA_ROOT", str(EXTENSION_ROOT / "wallpaper-media"))
).expanduser()
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/wallpapermaison-{os.getuid()}"))
INFO_FILE = Path(os.environ.get("WALLPAPERMAISON_VSCODE_MEDIA_INFO", str(RUNTIME_DIR / "wallpapermaison-vscode-media.json")))
LOCK_FILE = INFO_FILE.with_suffix(".lock")
MEDIA_NAME = re.compile(r"^[a-f0-9]{20}\.[a-z0-9]{2,5}$")
LOCAL_OPENER = build_opener(ProxyHandler({}))


def _read_info():
    try:
        data = json.loads(INFO_FILE.read_text(encoding="utf-8"))
        base_url = data.get("base_url", "")
        # The desktop session may define an HTTP proxy that rejects loopback
        # traffic. This endpoint is local by design and must bypass proxies.
        with LOCAL_OPENER.open(f"{base_url}/health", timeout=0.5) as response:
            if response.status == 200:
                return base_url
    except (OSError, ValueError, URLError):
        pass
    return None


def ensure_media_server(timeout: float = 8.0):
    """Start one loopback-only server per logged-in user and return its URL."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        running = _read_info()
        if running:
            return running

        log_dir = Path.home() / ".cache/wallpapermaison/logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = (log_dir / "vscode-media-server.log").open("a", encoding="utf-8")
        env = os.environ.copy()
        env["WALLPAPERMAISON_VSCODE_MEDIA_ROOT"] = str(MEDIA_ROOT)
        env["WALLPAPERMAISON_VSCODE_MEDIA_INFO"] = str(INFO_FILE)
        try:
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve"],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
                close_fds=True,
            )
        finally:
            log_file.close()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.1)
            running = _read_info()
            if running:
                return running
    return None


def media_url_for(media_path: str):
    path = Path(media_path).expanduser()
    try:
        path = path.resolve(strict=True)
        if path.parent != MEDIA_ROOT.resolve():
            return str(path)
        if not MEDIA_NAME.fullmatch(path.name):
            return str(path)
        base_url = ensure_media_server()
        if base_url:
            return f"{base_url}/media/{quote(path.name)}"
    except OSError:
        pass
    return str(path)


def _write_info(base_url: str, pid: int):
    INFO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=INFO_FILE.parent,
        prefix=f".{INFO_FILE.name}.", suffix=".tmp", delete=False
    ) as handle:
        temp_path = Path(handle.name)
        json.dump({"base_url": base_url, "pid": pid}, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, INFO_FILE)


def _make_handler(media_root: Path):
    class WallpaperMediaHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_HEAD(self):
            self._send_media(send_body=False)

        def do_GET(self):
            self._send_media(send_body=True)

        def _send_media(self, send_body: bool):
            request_path = urlsplit(self.path).path
            if request_path == "/health":
                body = b"ok\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if send_body:
                    self.wfile.write(body)
                return

            prefix = "/media/"
            name = unquote(request_path[len(prefix):]) if request_path.startswith(prefix) else ""
            if not MEDIA_NAME.fullmatch(name):
                self.send_error(404)
                return
            target = media_root / name
            try:
                stat = target.stat()
                if not target.is_file() or target.resolve().parent != media_root.resolve():
                    raise OSError("not a regular staged file")
            except OSError:
                self.send_error(404)
                return

            start, end, status = 0, stat.st_size - 1, 200
            range_header = self.headers.get("Range", "")
            if range_header.startswith("bytes="):
                try:
                    left, right = range_header[6:].split(",", 1)[0].split("-", 1)
                    start = int(left) if left else max(0, stat.st_size - int(right))
                    end = int(right) if right else stat.st_size - 1
                    if start > end or start >= stat.st_size:
                        raise ValueError("invalid byte range")
                    end = min(end, stat.st_size - 1)
                    status = 206
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{stat.st_size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

            length = max(0, end - start + 1)
            self.send_response(status)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{stat.st_size}")
            self.end_headers()
            if send_body:
                with target.open("rb") as source:
                    source.seek(start)
                    remaining = length
                    while remaining:
                        chunk = source.read(min(64 * 1024, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)

        def log_message(self, _format, *args):
            return

    return WallpaperMediaHandler


def serve_forever():
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(MEDIA_ROOT))
    server.daemon_threads = True
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    _write_info(base_url, os.getpid())
    server.serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        serve_forever()
    else:
        print(ensure_media_server() or "")
