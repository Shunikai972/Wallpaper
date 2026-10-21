#!/usr/bin/env python3
"""Génère la version patchée de workbench.html avec fond vidéo réactif, Monaco transparent et lecture ininterrompue."""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.automation.vscode_media import stage_media_for_vscode
from app.automation.vscode_media_server import media_url_for


def atomic_write_text(target: Path, text: str) -> None:
    """Replace a state file as a whole so renderers never read partial JSON."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

def detect_current_video_path(preferred_path: str = None) -> str:
    """Détecte avec certitude le fond d'écran vidéo actuellement actif sur le bureau."""
    if preferred_path and Path(preferred_path).exists():
        return str(Path(preferred_path).resolve())

    # Query the active renderer first; GSettings can lag behind a live change.
    if shutil.which("gdbus"):
        try:
            result = subprocess.run(
                [
                    "gdbus", "call", "--session", "--dest", "io.github.jeffshee.HanabiRenderer",
                    "--object-path", "/io/github/jeffshee/HanabiRenderer",
                    "--method", "io.github.jeffshee.HanabiRenderer.getFilePath",
                ],
                capture_output=True, text=True, timeout=1,
            )
            if result.returncode == 0:
                reply = ast.literal_eval(result.stdout.strip())
                active_path = reply[0] if isinstance(reply, tuple) and reply else ""
                if active_path and Path(active_path).is_file():
                    return str(Path(active_path).resolve())
        except (OSError, SyntaxError, ValueError, subprocess.SubprocessError):
            pass

    # Fall back to the configured path when an older renderer lacks getFilePath.
    if shutil.which("gsettings"):
        try:
            res = subprocess.run(
                ["gsettings", "get", "io.github.jeffshee.hanabi-extension", "video-path"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1
            )
            if res.returncode == 0:
                val = res.stdout.strip().strip("'\"")
                if val and Path(val).exists():
                    return str(Path(val).resolve())
        except Exception:
            pass

    # 2. Vérification fichier d'état WallpaperMaison
    state_files = [
        Path.home() / ".config/wallpapermaison/current_wallpaper.json",
        Path.home() / "reseau/Perso/.config/wallpapermaison/current_wallpaper.json"
    ]
    for sf in state_files:
        if sf.exists():
            try:
                st = json.loads(sf.read_text(encoding="utf-8"))
                p = st.get("path")
                if p and Path(p).exists():
                    return str(Path(p).resolve())
            except Exception:
                pass

    # 3. Vérification du symlink wallpaper.mp4
    symlinks = [
        Path.home() / "reseau/Perso/Téléchargements/wallpaper.mp4",
        Path.home() / "Téléchargements/wallpaper.mp4"
    ]
    for sl in symlinks:
        if sl.exists():
            return str(sl.resolve())

    # 4. Dossier Wallpaper du projet
    repo_wp = Path(__file__).resolve().parents[1] / "Wallpaper"
    if repo_wp.exists():
        repo_sl = repo_wp / "wallpaper.mp4"
        if repo_sl.exists():
            return str(repo_sl.resolve())
        repo_vids = sorted(list(repo_wp.glob("*.mp4")) + list(repo_wp.glob("*.webm")))
        if repo_vids:
            return str(repo_vids[0].resolve())

    # 5. Premier MP4 disponible dans les répertoires standards
    for dl_dir in [
        Path.home() / "reseau/Perso/Téléchargements",
        Path.home() / "Téléchargements",
        Path.home() / "Downloads",
        Path.home() / "Pictures/Wallpapers",
        Path.home() / "Wallpaper"
    ]:
        if dl_dir.exists():
            mp4s = list(dl_dir.glob("*.mp4")) + list(dl_dir.glob("*.webm"))
            if mp4s:
                return str(mp4s[0].resolve())

    default_target = repo_wp / "wallpaper.mp4"
    if default_target.exists():
        return str(default_target.resolve())
    return str(Path.home() / "Téléchargements/wallpaper.mp4")

def find_workbench_html() -> Path:
    """Trouve le HTML de démarrage de l'installation VS Code installée."""
    explicit = os.environ.get("WALLPAPERMAISON_VSCODE_HTML")
    roots = [
        Path("/usr/apps/VSCode-linux-x64"),
        Path("/usr/share/code"),
        Path("/usr/lib/code"),
        Path("/opt/visual-studio-code"),
        Path.home() / ".local/share/vscode",
    ]
    candidates = [Path(explicit)] if explicit else []
    candidates.extend(
        root / "resources/app/out/vs/code" / layout / "workbench/workbench.html"
        for root in roots
        for layout in ("electron-browser", "electron-sandbox")
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0] if candidates else Path(
        "/usr/apps/VSCode-linux-x64/resources/app/out/vs/code/electron-browser/workbench/workbench.html"
    )


def _strip_json_comments(source: str) -> str:
    """Remove JSONC comments without mistaking comment markers inside strings."""
    result = []
    index = 0
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
                result.append(char)
            index += 1
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                if char == "\n":
                    result.append(char)
                index += 1
            continue
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(char)
            index += 1
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 2
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 2
        else:
            result.append(char)
            index += 1
    return "".join(result)


def get_wallpaper_object_fit() -> str:
    """Respect the VS Code wallpaper size preference, defaulting to full stretch."""
    settings_files = [
        Path.home() / ".config/Code/User/settings.json",
        Path.home() / "reseau/Perso/.config/Code/User/settings.json",
    ]
    for settings_file in settings_files:
        try:
            source = _strip_json_comments(settings_file.read_text(encoding="utf-8"))
            settings = json.loads(re.sub(r",\s*([}\]])", r"\1", source))
            wallpaper = settings.get("liveWallpaper", {})
            size = wallpaper.get("size") if isinstance(wallpaper, dict) else None
            size = size or settings.get("liveWallpaper.size")
            if size in {"cover", "contain", "fill"}:
                return size
            if size == "auto":
                return "fill"
        except (OSError, json.JSONDecodeError, AttributeError, TypeError):
            continue
    return "fill"


def _add_csp_sources(content: str, directive: str, sources: list[str]) -> tuple[str, bool]:
    """Add sources to a CSP directive once, preserving unrelated directives."""
    pattern = re.compile(
        rf"(?P<head>(?<![\w-]){re.escape(directive)})(?=[\s;])(?P<body>[^;]*);",
        re.DOTALL,
    )
    found = False

    def add_missing(match: re.Match) -> str:
        nonlocal found
        found = True
        existing = set(match.group("body").split())
        missing = [source for source in sources if source and source not in existing]
        prefix = " " + " ".join(missing) if missing else ""
        return f"{match.group('head')}{prefix}{match.group('body')};"

    return pattern.sub(add_missing, content), found


def update_live_state(video_path: str, media_type: str = "video") -> None:
    """Met à jour les fichiers live_state (.json et .js) dans les extensions autorisées par VS Code."""
    import time
    resolved = str(Path(video_path).resolve()) if video_path else ""
    media_url = media_url_for(resolved) if resolved else ""
    st_data = {
        "path": media_url,
        "media_type": media_type,
        "source": "desktop",
        "timestamp": time.time()
    }
    js_code = f""";(function() {{
    var p = {json.dumps(media_url, ensure_ascii=True)};
    if (typeof window.__applyWallpaperMaisonMedia === 'function') {{
        window.__applyWallpaperMaisonMedia(p);
    }}
}})();\n"""

    targets = [
        Path("/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0"),
        Path.home() / ".vscode/extensions/budicuy.live-wallpaper-99.0.0",
        Path.home() / "reseau/Perso/.vscode/extensions/budicuy.live-wallpaper-99.0.0",
        Path.home() / ".config/wallpapermaison",
        Path.home() / "reseau/Perso/.config/wallpapermaison"
    ]

    for t_dir in targets:
        try:
            t_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(t_dir / "live_state.json", json.dumps(st_data, indent=2))
            atomic_write_text(t_dir / "live_state.js", js_code)
        except Exception:
            pass

def patch_workbench(video_path: str = None) -> bool:
    orig_path = find_workbench_html()
    if not orig_path.exists():
        return False

    resolved_video_path = detect_current_video_path(video_path)
    vscode_media_path = stage_media_for_vscode(resolved_video_path)

    vscode_media_url = media_url_for(vscode_media_path)
    media_parts = urlsplit(vscode_media_url)
    local_media_origin = ""
    if media_parts.scheme == "http" and media_parts.hostname in {"127.0.0.1", "localhost", "::1"}:
        local_media_origin = f"{media_parts.scheme}://{media_parts.netloc}"
    vsc_url = vscode_media_url
    wallpaper_object_fit = get_wallpaper_object_fit()

    # Mise à jour cohérente de current_wallpaper.json et live_state (.json et .js)
    state_files = [
        Path.home() / ".config/wallpapermaison/current_wallpaper.json",
        Path.home() / "reseau/Perso/.config/wallpapermaison/current_wallpaper.json"
    ]
    import time
    st_data = {
        "path": resolved_video_path,
        "media_type": "video",
        "source": "desktop",
        "timestamp": time.time()
    }
    for sf in state_files:
        try:
            atomic_write_text(sf, json.dumps(st_data, indent=2))
        except Exception:
            pass

    update_live_state(vscode_media_path, "video")

    content = orig_path.read_text(encoding="utf-8")

    # 1. Mise à jour CSP pour autoriser les médias locaux, scripts d'extension et connexions locales
    local_origins = ["http://127.0.0.1:*", "http://localhost:*", "http:"]
    if local_media_origin and local_media_origin not in local_origins:
        local_origins.append(local_media_origin)
    content, _ = _add_csp_sources(content, "script-src", ["'unsafe-inline'", "vscode-file:"])
    content, _ = _add_csp_sources(content, "media-src", [
        "'self'", "vscode-file:", "vscode-remote-resource:",
        "https:", "blob:", "data:", *local_origins,
    ])
    content, _ = _add_csp_sources(content, "img-src", [
        "'self'", "vscode-file:", "vscode-remote-resource:",
        "https:", "blob:", "data:", *local_origins,
    ])
    content, has_connect_src = _add_csp_sources(content, "connect-src", [
        "'self'", "vscode-file:", "vscode-remote-resource:", "https:", "http:", "ws:", "wss:",
        "http://127.0.0.1:*", "http://localhost:*", "ws://127.0.0.1:*", "ws://localhost:*",
    ])
    if not has_connect_src:
        content = re.sub(
            r"default-src\s+'none'\s*;",
            "default-src 'none';\\n\\t\\t\\t\\tconnect-src 'self' vscode-file: vscode-remote-resource: https: http: ws: wss: http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*;",
            content,
            count=1,
        )
    content = re.sub(r"require-trusted-types-for[^;]*;", "", content)
    content = re.sub(r"trusted-types[^;]*;", "", content)

    # 2. Nettoyage de patches précédents
    content = re.sub(r"<!-- live-wallpaper-start.*?<!-- live-wallpaper-end -->\n?", "", content, flags=re.DOTALL)

    # 3. Injection CSS & JS
    patch_code = f"""<!-- live-wallpaper-start live-wallpaper.ver.99.0.0 -->
<style id="live-wallpaper-injected-style">
    /* Suppression des alertes de corruption */
    .notification-toast-container:has([aria-label*="corrupt"]) {{ display: none !important; }}

    /* Keep the normal VS Code theme opaque until a wallpaper is actually decoded. */
    body.wallpapermaison-live-ready,
    body.wallpapermaison-live-ready .monaco-workbench,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor > .content,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .editor-group-container,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .editor-group-watermark,
    /* The primary grid is a sibling of .part.editor and otherwise stays opaque. */
    body.wallpapermaison-live-ready .monaco-workbench .monaco-grid-view,
    body.wallpapermaison-live-ready .monaco-workbench .monaco-grid-view .monaco-grid-branch-node,
    body.wallpapermaison-live-ready .monaco-workbench .monaco-grid-view .split-view-view,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .monaco-grid-view,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .monaco-grid-branch-node,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .empty,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .split-view-view,
    body.wallpapermaison-live-ready .monaco-workbench .part.editor .editor-container,
    body.wallpapermaison-live-ready .monaco-editor,
    body.wallpapermaison-live-ready .monaco-editor-background,
    body.wallpapermaison-live-ready .monaco-editor .inputarea.ime-input,
    body.wallpapermaison-live-ready .monaco-editor .margin,
    body.wallpapermaison-live-ready .monaco-editor .monaco-scrollable-element,
    body.wallpapermaison-live-ready .monaco-editor .overflow-guard,
    body.wallpapermaison-live-ready .monaco-editor .view-lines,
    body.wallpapermaison-live-ready .monaco-editor .view-line {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    .monaco-workbench .part.editor .editor-group-watermark .letterpress {{
        opacity: 0.75 !important;
    }}

    /* Le conteneur principal de l'éditeur doit être au-dessus du fond vidéo */
    .monaco-workbench {{
        position: relative !important;
        z-index: 1 !important;
    }}

    /* Amélioration absolue de la lisibilité des lignes de code */
    .monaco-editor .view-lines {{
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95), 0 0 1px rgba(0, 0, 0, 0.95) !important;
    }}
    .monaco-editor .lines-content {{
        background-color: rgba(13, 17, 23, 0.40) !important;
        border-radius: 4px !important;
    }}

    /* Vidéo ou Image de fond : calque d'arrière-plan fluide (z-index 0 pour ne pas superposer le texte) */
    #live-wallpaper-bg-video, #live-wallpaper-bg-img, .live-wallpaper-media {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        object-fit: {wallpaper_object_fit} !important;
        opacity: 0.35 !important;
        z-index: 0 !important;
        pointer-events: none !important;
        display: block !important;
        transition: opacity 0.3s ease-in-out !important;
    }}

    /* Bouton SUDO : Intégration native dans la Barre d'Activité latérale */
    .part.activitybar .action-item.sudo-root-item {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 48px !important;
        height: 48px !important;
        cursor: pointer !important;
        position: relative !important;
        margin: 2px 0 !important;
        user-select: none !important;
    }}

    .part.activitybar .action-item.sudo-root-item a.action-label {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 38px !important;
        height: 38px !important;
        border-radius: 6px !important;
        transition: background-color 0.15s ease, transform 0.1s ease !important;
    }}

    .part.activitybar .action-item.sudo-root-item:hover a.action-label {{
        background-color: rgba(239, 68, 68, 0.2) !important;
        transform: scale(1.06) !important;
    }}

    .part.activitybar .action-item.sudo-root-item:hover svg {{
        filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.8)) !important;
    }}

    .part.activitybar .action-item.sudo-root-item:active a.action-label {{
        transform: scale(0.92) !important;
    }}

    /* Indicateur latéral d'activation comme les icônes officielles VS Code */
    .part.activitybar .action-item.sudo-root-item::before {{
        content: '';
        position: absolute;
        left: 0;
        top: 10px;
        height: 28px;
        width: 2px;
        background-color: #ef4444;
        opacity: 0;
        transition: opacity 0.2s ease;
    }}

    .part.activitybar .action-item.sudo-root-item:hover::before {{
        opacity: 1;
    }}

    /* Bouton de secours si la barre tarde à s'afficher */
    #vsc-sudo-action-btn-fallback {{
        position: fixed;
        bottom: 60px;
        left: 6px;
        width: 36px;
        height: 36px;
        z-index: 100000;
        background: rgba(239, 68, 68, 0.25);
        border: 1px solid #ef4444;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5);
        transition: transform 0.15s ease;
    }}
    #vsc-sudo-action-btn-fallback:hover {{
        transform: scale(1.1);
        background: rgba(239, 68, 68, 0.4);
    }}
</style>

<script>
;(function() {{
    var LW_VIDEO_ID = 'live-wallpaper-bg-video';
    var LW_IMG_ID = 'live-wallpaper-bg-img';
    var currentMediaSrc = {repr(vsc_url)};
    var currentRawPath = {json.dumps(vscode_media_url, ensure_ascii=True)};

    function normalizeMediaPath(p) {{
        if (!p) return '';
        var value = String(p);
        try {{
            if (value.startsWith('vscode-file://') || value.startsWith('file://')) {{
                value = new URL(value).pathname;
            }}
            value = decodeURIComponent(value);
        }} catch (e) {{}}
        return value.replace(/\\\\/g, '/');
    }}

    function isVideoSrc(src) {{
        if (!src) return true;
        var clean = src.split('?')[0].toLowerCase();
        return clean.endsWith('.mp4') || clean.endsWith('.webm') || clean.endsWith('.mkv') || !clean.match(/\\.(png|jpe?g|webp|gif|bmp|svg)$/);
    }}

    function toVscUrl(p) {{
        if (!p) return '';
        if (p.startsWith('vscode-file://') || p.startsWith('http://') || p.startsWith('https://') || p.startsWith('data:') || p.startsWith('blob:')) return p;
        var clean = p.startsWith('file://') ? p.slice(7) : p;
        var encodedPath = clean.split('/').map(function(part, index) {{
            if (index === 0 && part === '') return '';
            try {{ return encodeURIComponent(decodeURIComponent(part)); }}
            catch (e) {{ return encodeURIComponent(part); }}
        }}).join('/');
        return 'vscode-file://vscode-app' + encodedPath;
    }}

    function applyMedia(rawSrc) {{
        if (!rawSrc) return;
        var src = toVscUrl(rawSrc);

        // Keep one decoder per requested wallpaper while its first frame loads.
        // The element gets its public id only after decoding, so the body
        // observer otherwise treats it as missing and starts duplicate videos.
        if (pendingMedia && document.body.contains(pendingMedia)) {{
            var pendingSrc = pendingMedia.currentSrc || pendingMedia.src || '';
            if (normalizeMediaPath(pendingSrc) === normalizeMediaPath(src)) return;
            try {{ pendingMedia.pause(); }} catch (e) {{}}
            try {{ pendingMedia.remove(); }} catch (e) {{}}
            pendingMedia = null;
        }}

        var oldVid = document.getElementById(LW_VIDEO_ID);
        var oldImg = document.getElementById(LW_IMG_ID);
        var sameMedia = normalizeMediaPath(currentRawPath) === normalizeMediaPath(rawSrc);

        // Si le même fond est déjà actif et en cours de lecture, ne rien recharger
        if (sameMedia && (oldVid || oldImg)) {{
            if (oldVid && oldVid.paused) {{
                oldVid.play().catch(function() {{}});
            }}
            return;
        }}
        if (sameMedia && failedMediaPath === normalizeMediaPath(rawSrc)) return;

        currentMediaSrc = src;
        currentRawPath = rawSrc;
        failedMediaPath = '';

        var targetOpacity = '0.35';
        var objectFit = {json.dumps(wallpaper_object_fit)};
        var commonStyle = [
            'position: fixed !important',
            'top: 0 !important',
            'left: 0 !important',
            'width: 100vw !important',
            'height: 100vh !important',
            'object-fit: ' + objectFit + ' !important',
            'z-index: 0 !important',
            'pointer-events: none !important',
            'display: block !important',
            'transition: opacity 0.3s ease-in-out !important'
        ].join(';');

        if (isVideoSrc(src)) {{
            var newVideo = document.createElement('video');
            newVideo.muted = true;
            newVideo.defaultMuted = true;
            newVideo.autoplay = true;
            newVideo.loop = true;
            newVideo.playsInline = true;
            newVideo.preload = 'auto';

            newVideo.setAttribute('muted', '');
            newVideo.setAttribute('autoplay', '');
            newVideo.setAttribute('loop', '');
            newVideo.setAttribute('playsinline', '');
            newVideo.setAttribute('webkit-playsinline', '');

            // Double-buffering : on démarre à opacity 0 si un ancien média est déjà actif pour éliminer le blackscreen
            var hasPrevious = !!(oldVid || oldImg);
            pendingMedia = newVideo;
            newVideo.style.cssText = commonStyle + '; opacity: ' + (hasPrevious ? '0' : targetOpacity) + ' !important;';

            var cleanedUp = false;
            var readyScheduled = false;
            function onMediaReady() {{
                if (cleanedUp || readyScheduled || pendingMedia !== newVideo) return;
                readyScheduled = true;
                var reveal = function() {{
                    if (cleanedUp || pendingMedia !== newVideo) return;
                    cleanedUp = true;
                    pendingMedia = null;
                    console.log("[WallpaperMaison] Vidéo prête dans VS Code:", newVideo.currentSrc, newVideo.videoWidth + 'x' + newVideo.videoHeight);
                    document.body.classList.add('wallpapermaison-live-ready');
                    newVideo.id = LW_VIDEO_ID;
                    newVideo.style.opacity = targetOpacity;
                    if (oldVid && oldVid !== newVideo) {{
                        oldVid.style.opacity = '0';
                        setTimeout(function() {{ try {{ oldVid.remove(); }} catch(e) {{}} }}, 350);
                    }}
                    if (oldImg) {{
                        oldImg.style.opacity = '0';
                        setTimeout(function() {{ try {{ oldImg.remove(); }} catch(e) {{}} }}, 350);
                    }}
                }};
                if (typeof newVideo.requestVideoFrameCallback === 'function') {{
                    newVideo.requestVideoFrameCallback(reveal);
                }} else {{
                    requestAnimationFrame(reveal);
                }}
            }}

            newVideo.oncanplay = function() {{
                if (newVideo.paused) newVideo.play().catch(function() {{}});
            }};
            newVideo.onloadeddata = function() {{
                if (newVideo.paused) newVideo.play().catch(function() {{}});
            }};
            newVideo.onplaying = function() {{
                onMediaReady();
            }};
            newVideo.onended = function() {{
                newVideo.currentTime = 0;
                newVideo.play().catch(function() {{}});
            }};
            newVideo.onerror = function(e) {{
                if (pendingMedia !== newVideo) return;
                pendingMedia = null;
                var mediaError = newVideo.error;
                var diagnostic = {{
                    path: rawSrc,
                    currentSrc: newVideo.currentSrc,
                    code: mediaError ? mediaError.code : null,
                    message: mediaError ? mediaError.message : '',
                    readyState: newVideo.readyState,
                    networkState: newVideo.networkState,
                    eventType: e && e.type
                }};
                console.warn("[WallpaperMaison] Erreur chargement vidéo: " + JSON.stringify(diagnostic));
                failedMediaPath = normalizeMediaPath(rawSrc);
                try {{ newVideo.remove(); }} catch(err) {{}}
                if (!oldVid && !oldImg) document.body.classList.remove('wallpapermaison-live-ready');
            }};

            newVideo.src = src;
            document.body.appendChild(newVideo);
            newVideo.play().catch(function(error) {{
                console.warn("[WallpaperMaison] Lecture vidéo refusée:", rawSrc, error && error.name, error && error.message);
            }});

            // Remove an undecodable media source without making the whole workbench transparent.
            setTimeout(function() {{
                if (pendingMedia === newVideo && !cleanedUp && document.body.contains(newVideo)) {{
                    console.warn("[WallpaperMaison] Délai de décodage dépassé:", {{
                        path: rawSrc,
                        currentSrc: newVideo.currentSrc,
                        code: newVideo.error ? newVideo.error.code : null,
                        readyState: newVideo.readyState,
                        networkState: newVideo.networkState
                    }});
                    failedMediaPath = normalizeMediaPath(rawSrc);
                    pendingMedia = null;
                    try {{ newVideo.remove(); }} catch(e) {{}}
                    if (!oldVid && !oldImg) document.body.classList.remove('wallpapermaison-live-ready');
                }}
            }}, 15000);

        }} else {{
            var newImg = document.createElement('img');
            var hasPrevious = !!(oldVid || oldImg);
            pendingMedia = newImg;
            newImg.style.cssText = commonStyle + '; opacity: ' + (hasPrevious ? '0' : targetOpacity) + ' !important;';
            newImg.onload = function() {{
                if (pendingMedia !== newImg) return;
                pendingMedia = null;
                document.body.classList.add('wallpapermaison-live-ready');
                newImg.id = LW_IMG_ID;
                newImg.style.opacity = targetOpacity;
                if (oldVid) {{
                    oldVid.style.opacity = '0';
                    setTimeout(function() {{ try {{ oldVid.remove(); }} catch(e) {{}} }}, 350);
                }}
                if (oldImg && oldImg !== newImg) {{
                    oldImg.style.opacity = '0';
                    setTimeout(function() {{ try {{ oldImg.remove(); }} catch(e) {{}} }}, 350);
                }}
            }};
            newImg.onerror = function() {{
                if (pendingMedia !== newImg) return;
                pendingMedia = null;
                failedMediaPath = normalizeMediaPath(rawSrc);
                try {{ newImg.remove(); }} catch(e) {{}}
                if (!oldVid && !oldImg) document.body.classList.remove('wallpapermaison-live-ready');
            }};
            newImg.src = src;
            document.body.appendChild(newImg);
        }}
    }}

    window.__applyWallpaperMaisonMedia = applyMedia;

    function ensureMedia() {{
        if (pendingMedia && document.body.contains(pendingMedia)) return;
        var vid = document.getElementById(LW_VIDEO_ID);
        var img = document.getElementById(LW_IMG_ID);
        if (!vid && !img) {{
            if (currentRawPath) {{
                if (failedMediaPath !== normalizeMediaPath(currentRawPath)) applyMedia(currentRawPath);
            }} else if (currentMediaSrc) {{
                applyMedia(currentMediaSrc);
            }}
        }} else if (vid && vid.paused) {{
            vid.play().catch(function() {{}});
        }}
    }}

    function openSudoTerminal(e) {{
        if (e) {{ e.preventDefault(); e.stopPropagation(); }}
        console.log("[WallpaperMaison] Déclenchement du Terminal Sudo Root...");

        // Déclenchement via DOM (item terminal, statusbar item ou bouton activity bar)
        var candidates = [
            document.getElementById('sudoRootStatusItem'),
            document.querySelector('[id*="sudoRoot"]'),
            document.querySelector('.statusbar-item[aria-label*="Sudo"]'),
            document.querySelector('.statusbar-item[aria-label*="Root"]'),
            document.querySelector('.action-item [aria-label*="Terminal"]'),
            document.querySelector('.panel [aria-label*="Terminal"]')
        ];
        for (var i = 0; i < candidates.length; i++) {{
            if (candidates[i]) {{
                candidates[i].click();
                return;
            }}
        }}
    }}

    function injectSudoButton() {{
        var existingNative = document.getElementById('sudo-root-activity-action');
        var activityContainer = document.querySelector('.part.activitybar .composite-bar ul.actions-container') ||
                                document.querySelector('.part.activitybar ul.actions-container') ||
                                document.querySelector('.part.activitybar [role="toolbar"] ul') ||
                                document.querySelector('.activitybar .monaco-action-bar ul');

        if (existingNative) return;

        var li = document.createElement('li');
        li.className = 'action-item sudo-root-item';
        li.id = 'sudo-root-activity-action';
        li.setAttribute('role', 'tab');
        li.setAttribute('tabindex', '0');

        var a = document.createElement('a');
        a.className = 'action-label';
        a.setAttribute('role', 'button');
        a.setAttribute('aria-label', '⚡ Sudo Root : Ouvrir le Terminal Administrateur Root');
        a.title = '⚡ Sudo Root : Ouvrir le Terminal Administrateur Root (Sans mot de passe)';

        // Création SVG 100% conforme sans innerHTML pour contourner TrustedTypes
        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('width', '22');
        svg.setAttribute('height', '22');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', '#ef4444');
        svg.setAttribute('stroke-width', '1.8');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');

        var p1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        p1.setAttribute('d', 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z');
        svg.appendChild(p1);

        var p2 = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        p2.setAttribute('points', '13 7 8 13 12 13 11 17 16 11 12 11 13 7');
        p2.setAttribute('fill', '#ef4444');
        svg.appendChild(p2);

        a.appendChild(svg);
        li.appendChild(a);
        li.onclick = openSudoTerminal;
        a.onclick = openSudoTerminal;

        if (activityContainer) {{
            var oldFb = document.getElementById('vsc-sudo-action-btn-fallback');
            if (oldFb) oldFb.remove();
            activityContainer.appendChild(li);
        }} else {{
            if (!document.getElementById('vsc-sudo-action-btn-fallback')) {{
                li.id = 'vsc-sudo-action-btn-fallback';
                document.body.appendChild(li);
            }}
        }}
    }}

    function startLiveSyncWatcher() {{
        var userHome = {repr(str(Path.home()))};
        var jsonUrls = [
            'vscode-file://vscode-app/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0/live_state.json',
            'vscode-file://vscode-app' + encodeURI(userHome) + '/.vscode/extensions/budicuy.live-wallpaper-99.0.0/live_state.json'
        ];
        var scriptUrls = [
            'vscode-file://vscode-app/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0/live_state.js',
            'vscode-file://vscode-app' + encodeURI(userHome) + '/.vscode/extensions/budicuy.live-wallpaper-99.0.0/live_state.js'
        ];

        function checkLiveState() {{
            // vscode-file treats a query string as part of its disk path. Ask
            // the protocol for the stable URL and rely on cache: no-store.
            var target = jsonUrls[0];
            fetch(target, {{ cache: 'no-store' }})
                .then(function(res) {{
                    if (!res.ok) throw new Error('status ' + res.status);
                    return res.json();
                }})
                .then(function(data) {{
                    if (data && data.path && normalizeMediaPath(data.path) !== normalizeMediaPath(currentRawPath)) {{
                        console.log("[WallpaperMaison] Fond d'écran mis à jour en direct (fetch):", data.path);
                        applyMedia(data.path);
                    }}
                }})
                .catch(function() {{
                    // Fallback vers balise script
                    var old = document.getElementById('lw-live-script-dyn');
                    if (old) old.remove();
                    var s = document.createElement('script');
                    s.id = 'lw-live-script-dyn';
                    // A fragment busts Chromium's resource cache without
                    // becoming part of the vscode-file path on disk.
                    s.src = scriptUrls[0] + '#t=' + Date.now();
                    document.head.appendChild(s);
                }});
        }}

        setInterval(checkLiveState, 800);

        // 1. Écoute des messages
        window.addEventListener('message', function(e) {{
            if (e && e.data && e.data.type === 'wallpapermaison:state') {{
                var d = typeof e.data.data === 'string' ? JSON.parse(e.data.data) : e.data.data;
                if (d && d.path) applyMedia(d.path);
            }}
        }});

        // 2. Écoute des événements personnalisés
        window.addEventListener('wallpaper:change', function(e) {{
            if (e && e.detail && e.detail.path) applyMedia(e.detail.path);
        }});
    }}

    var failedMediaPath = '';
    var pendingMedia = null;
    var initialized = false;
    function init() {{
        if (initialized || !document.body) return;
        initialized = true;
        ensureMedia();
        injectSudoButton();
        startLiveSyncWatcher();

        // Observation dynamique pour réinsérer le bouton Sudo dès l'apparition de l'Activity Bar
        var observer = new MutationObserver(function() {{
            var act = document.querySelector('.part.activitybar ul.actions-container') ||
                      document.querySelector('.part.activitybar .composite-bar ul.actions-container') ||
                      document.querySelector('.part.activitybar [role="toolbar"] ul') ||
                      document.querySelector('.activitybar .monaco-action-bar ul');
            if (act && (!document.getElementById('sudo-root-activity-action') || document.getElementById('vsc-sudo-action-btn-fallback'))) {{
                injectSudoButton();
            }}
        }});
        observer.observe(document.body, {{ childList: true, subtree: true }});

        // VS Code may replace the initial body contents while mounting its workbench.
        // Restore the media layer if that happens after DOMContentLoaded.
        var bodyObserver = new MutationObserver(function() {{
            ensureMedia();
        }});
        bodyObserver.observe(document.body, {{ childList: true }});
        window.__wallpaperMaisonBodyObserver = bodyObserver;

        window.addEventListener('focus', ensureMedia);
        document.addEventListener('visibilitychange', function() {{
            if (document.visibilityState === 'visible') ensureMedia();
        }});
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', init, {{ once: true }});
    }} else {{
        setTimeout(init, 0);
    }}
}})();
</script>
<!-- live-wallpaper-end -->"""

    content = content.replace("</html>", patch_code + "\n</html>")

    # Keep the patched HTML and its relative JS beside each other. The launcher
    # bind-mounts this directory into VS Code so atomic HTML replacement remains
    # visible inside an already-running Bubblewrap namespace.
    workbench_js = orig_path.with_name("workbench.js")
    try:
        workbench_js_content = workbench_js.read_text(encoding="utf-8")
    except OSError:
        workbench_js_content = None

    overlay_dirs = [
        Path.home() / "reseau/Perso/.config/wallpapermaison/vscode/workbench",
        Path.home() / ".config/wallpapermaison/vscode/workbench",
    ]
    overlay_written = False
    for target_dir in overlay_dirs:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if orig_path.parent.is_dir():
                for sibling in orig_path.parent.iterdir():
                    if sibling.is_file() and sibling.name != "workbench.html":
                        try:
                            dest = target_dir / sibling.name
                            if not dest.exists() or dest.stat().st_mtime < sibling.stat().st_mtime:
                                shutil.copy2(sibling, dest)
                        except Exception:
                            pass
            atomic_write_text(target_dir / "workbench.html", content)
            if workbench_js_content is not None or (target_dir / "workbench.js").exists():
                overlay_written = True
        except Exception:
            pass

    # Keep legacy copies for installations or launchers that still bind one file.
    targets = [
        Path.home() / "reseau/Perso/.config/wallpapermaison/vscode/workbench.html",
        Path.home() / ".config/wallpapermaison/vscode/workbench.html",
        Path.home() / "reseau/Perso/.local/share/vscode/resources/app/out/vs/code/electron-browser/workbench/workbench.html",
        Path.home() / ".local/share/vscode/resources/app/out/vs/code/electron-browser/workbench/workbench.html"
    ]

    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(t, content)
        except Exception:
            pass

    return overlay_written

def patch_preload() -> bool:
    # Ne PAS patcher preload.js dans le bac à sable Electron (sandbox)
    # L'original de VS Code doit être préservé sans altération pour garantir
    # le bon démarrage de tous les services de fenêtres et boutons Monaco.
    targets = [
        Path.home() / "reseau/Perso/.config/wallpapermaison/vscode/preload.js",
        Path.home() / ".config/wallpapermaison/vscode/preload.js",
        Path.home() / "reseau/Perso/.local/share/vscode/resources/app/out/vs/base/parts/sandbox/electron-browser/preload.js",
        Path.home() / ".local/share/vscode/resources/app/out/vs/base/parts/sandbox/electron-browser/preload.js"
    ]
    for t in targets:
        try:
            if t.exists():
                t.unlink()
        except Exception:
            pass
    return True

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else None
    ok1 = patch_workbench(v_path)
    ok2 = patch_preload()
    sys.exit(0 if (ok1 and ok2) else 1)
