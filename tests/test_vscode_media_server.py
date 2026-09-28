"""Integration checks for the loopback server used by the VS Code workbench."""

import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

from app.automation import vscode_media_server as media_server


class TestVsCodeMediaServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.media = self.root / "0123456789abcdefabcd.mp4"
        self.media.write_bytes(b"0123456789abcdefghijklmnopqrstuvwxyz")
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), media_server._make_handler(self.root)
        )
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def test_health_check_bypasses_desktop_http_proxy(self):
        info_file = self.root / "server.json"
        info_file.write_text(
            json.dumps({"base_url": self.base_url}), encoding="utf-8"
        )
        with patch.object(media_server, "INFO_FILE", info_file), patch.dict(
            os.environ,
            {"HTTP_PROXY": "http://127.0.0.1:1", "NO_PROXY": ""},
        ):
            self.assertEqual(media_server._read_info(), self.base_url)

    def test_video_range_returns_partial_h264_response(self):
        request = Request(
            f"{self.base_url}/media/{self.media.name}",
            headers={"Range": "bytes=4-11"},
        )
        with media_server.LOCAL_OPENER.open(request, timeout=2) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.headers["Content-Type"], "video/mp4")
            self.assertEqual(response.headers["Content-Range"], "bytes 4-11/36")
            self.assertEqual(response.read(), b"456789ab")


if __name__ == "__main__":
    unittest.main()
