#!/usr/bin/env python3
"""Génère la version patchée de workbench.html avec fond vidéo réactif, Monaco transparent et lecture ininterrompue."""

import json
import os
import re
import sys
from pathlib import Path

def patch_workbench(video_path: str = None) -> bool:
    orig_path = Path("/usr/apps/VSCode-linux-x64/resources/app/out/vs/code/electron-browser/workbench/workbench.html")
    if not orig_path.exists():
        return False

    state_file = Path.home() / ".config/wallpapermaison/current_wallpaper.json"
    if not video_path:
        if state_file.exists():
            try:
                st = json.loads(state_file.read_text(encoding="utf-8"))
                video_path = st.get("path")
            except Exception:
                pass
    if not video_path:
        video_path = str(Path.home() / "reseau/Perso/Téléchargements/wallpaper.mp4")

    # Format vscode-file:// avec quote pour préserver les accents (ex: Téléchargements -> T%C3%A9l%C3%A9chargements)
    from urllib.parse import quote
    if not str(video_path).startswith("vscode-file://"):
        resolved_path = Path(video_path).resolve()
        quoted_path = quote(str(resolved_path), safe="/:@!$&'()*+,;=-_.~")
        vsc_url = f"vscode-file://vscode-app{quoted_path}"
    else:
        vsc_url = str(video_path)

    user = os.environ.get("USER", "E256190S")
    state_urls = [
        f"vscode-file://vscode-app{quote(str(Path.home() / '.config/wallpapermaison/current_wallpaper.json'), safe='/:@!$&()*+,;=-_.~')}",
        f"vscode-file://vscode-app{quote(str(Path.home() / 'reseau/Perso/.config/wallpapermaison/current_wallpaper.json'), safe='/:@!$&()*+,;=-_.~')}",
        f"vscode-file://vscode-app/var/home/{user}/.config/wallpapermaison/current_wallpaper.json",
        f"vscode-file://vscode-app/var/home/{user}/reseau/Perso/.config/wallpapermaison/current_wallpaper.json"
    ]
    seen = set()
    state_urls_dedup = []
    for u in state_urls:
        if u not in seen:
            seen.add(u)
            state_urls_dedup.append(u)
    state_urls_json = json.dumps(state_urls_dedup)

    content = orig_path.read_text(encoding="utf-8")

    # 1. Mise à jour CSP
    content = content.replace("script-src", "script-src 'unsafe-inline'")
    content = content.replace("media-src", "media-src 'self' vscode-file: vscode-remote-resource: https: blob: data:")
    content = content.replace("img-src", "img-src 'self' vscode-file: vscode-remote-resource: https: blob: data:")
    content = content.replace("connect-src", "connect-src 'self' vscode-file: vscode-remote-resource: https: ws: http:")
    content = re.sub(r"require-trusted-types-for[^;]*;", "", content)
    content = re.sub(r"trusted-types[^;]*;", "", content)

    # 2. Nettoyage de patches précédents
    content = re.sub(r"<!-- live-wallpaper-start.*?<!-- live-wallpaper-end -->\n?", "", content, flags=re.DOTALL)

    # 3. Injection CSS & JS
    patch_code = f"""<!-- live-wallpaper-start live-wallpaper.ver.1.0.14 -->
<style id="live-wallpaper-injected-style">
    /* Suppression des alertes de corruption */
    .notification-toast-container:has([aria-label*="corrupt"]) {{ display: none !important; }}

    /* Transparence absolue de TOUTES les couches Monaco Editor */
    .monaco-workbench,
    .monaco-workbench .part.editor,
    .monaco-workbench .part.editor > .content,
    .monaco-workbench .part.editor .editor-group-container,
    .monaco-workbench .part.editor .editor-group-watermark,
    .monaco-workbench .part.editor .monaco-grid-view,
    .monaco-workbench .part.editor .monaco-grid-branch-node,
    .monaco-workbench .part.editor .empty,
    .monaco-workbench .part.editor .split-view-view,
    .monaco-workbench .part.editor .editor-container,
    .monaco-editor,
    .monaco-editor-background,
    .monaco-editor .inputarea.ime-input,
    .monaco-editor .margin,
    .monaco-editor .monaco-scrollable-element,
    .monaco-editor .overflow-guard,
    .monaco-editor .view-lines,
    .monaco-editor .view-line {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    .monaco-workbench .part.editor .editor-group-watermark .letterpress {{
        opacity: 0.75 !important;
    }}

    /* Vidéo ou Image de fond : persistance absolue au-dessus des arrière-plans mais transparente */
    #{'live-wallpaper-bg-video'}, #{'live-wallpaper-bg-img'} {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        object-fit: cover !important;
        opacity: 0.35 !important;
        z-index: 999 !important;
        pointer-events: none !important;
        display: block !important;
    }}
</style>

<script>
;(function() {{
    var STATE_URLS = {state_urls_json};
    var LW_VIDEO_ID = 'live-wallpaper-bg-video';
    var LW_IMG_ID = 'live-wallpaper-bg-img';
    var currentMediaSrc = {repr(vsc_url)};
    var currentRawPath = {repr(str(video_path))};

    function isVideoSrc(src) {{
        if (!src) return true;
        var clean = src.split('?')[0].toLowerCase();
        return clean.endsWith('.mp4') || clean.endsWith('.webm') || clean.endsWith('.mkv') || !clean.match(/\\.(png|jpe?g|webp|gif|bmp|svg)$/);
    }}

    function toVscUrl(p) {{
        if (!p) return '';
        if (p.startsWith('vscode-file://')) return p;
        return 'vscode-file://vscode-app' + encodeURI(p);
    }}

    function applyMedia(rawSrc) {{
        if (!rawSrc) return;
        var src = toVscUrl(rawSrc);
        var oldVid = document.getElementById(LW_VIDEO_ID);
        var oldImg = document.getElementById(LW_IMG_ID);

        if (currentMediaSrc === src && (oldVid || oldImg)) {{
            if (oldVid && oldVid.paused) oldVid.play().catch(function() {{}});
            return;
        }}

        currentMediaSrc = src;
        currentRawPath = rawSrc;

        if (oldVid) oldVid.remove();
        if (oldImg) oldImg.remove();

        if (isVideoSrc(src)) {{
            var video = document.createElement('video');
            video.id = LW_VIDEO_ID;
            video.src = src;
            video.autoplay = true;
            video.loop = true;
            video.muted = true;
            video.defaultMuted = true;
            video.playsInline = true;
            video.setAttribute('playsinline', '');
            video.setAttribute('webkit-playsinline', '');
            video.setAttribute('muted', '');
            video.onerror = function(e) {{
                console.error("[WallpaperMaison] Erreur lecture vidéo:", e);
            }};
            video.addEventListener('pause', function() {{
                setTimeout(function() {{
                    var v = document.getElementById(LW_VIDEO_ID);
                    if (v && v.paused) v.play().catch(function() {{}});
                }}, 20);
            }});
            document.body.appendChild(video);
            video.load();
            video.play().catch(function() {{}});
        }} else {{
            var img = document.createElement('img');
            img.id = LW_IMG_ID;
            img.src = src;
            document.body.appendChild(img);
        }}
    }}

    function ensureMedia() {{
        var vid = document.getElementById(LW_VIDEO_ID);
        var img = document.getElementById(LW_IMG_ID);
        if (!vid && !img) {{
            if (currentMediaSrc) applyMedia(currentMediaSrc);
        }} else if (vid && vid.paused) {{
            vid.play().catch(function() {{}});
        }}
    }}

    function startLiveSyncWatcher() {{
        function applyState(raw) {{
            try {{
                if (!raw) return;
                var data = typeof raw === 'string' ? JSON.parse(raw) : raw;
                if (data && data.path) {{
                    var target = toVscUrl(data.path);
                    if (target !== currentMediaSrc) {{
                        console.log("[WallpaperMaison] Synchronisation dynamique du fond:", target);
                        applyMedia(target);
                    }}
                }}
            }} catch(e) {{}}
        }}

        // 1. Écoute des messages
        window.addEventListener('message', function(e) {{
            if (e && e.data && e.data.type === 'wallpapermaison:state') {{
                applyState(e.data.data);
            }}
        }});

        // 2. Sondage direct continu via fetch / XMLHttpRequest
        function pollStateFiles() {{
            for (var i = 0; i < STATE_URLS.length; i++) {{
                (function(url) {{
                    var u = url + '?_t=' + Date.now();
                    if (typeof fetch === 'function') {{
                        fetch(u, {{ cache: 'no-store' }})
                            .then(function(res) {{
                                if (res.ok) return res.json();
                                throw new Error(res.status);
                            }})
                            .then(function(data) {{
                                applyState(data);
                            }})
                            .catch(function() {{
                                try {{
                                    var xhr = new XMLHttpRequest();
                                    xhr.open('GET', u, true);
                                    xhr.onload = function() {{
                                        if (xhr.status === 200 || xhr.status === 0) {{
                                            applyState(xhr.responseText);
                                        }}
                                    }};
                                    xhr.send();
                                }} catch(e) {{}}
                            }});
                    }}
                }})(STATE_URLS[i]);
            }}
        }}

        setInterval(pollStateFiles, 200);
        pollStateFiles();
    }}

    function init() {{
        ensureMedia();
        startLiveSyncWatcher();

        setInterval(ensureMedia, 500);
        window.addEventListener('focus', ensureMedia);
        window.addEventListener('keydown', function() {{ setTimeout(ensureMedia, 50); }});
        document.addEventListener('visibilitychange', function() {{
            if (document.visibilityState === 'visible') ensureMedia();
        }});
    }}

    if (document.readyState === 'complete' || document.body) {{
        init();
    }} else {{
        document.addEventListener('DOMContentLoaded', init);
    }}
}})();
</script>
<!-- live-wallpaper-end -->"""

    content = content.replace("</html>", patch_code + "\n</html>")

    targets = [
        Path.home() / "reseau/Perso/.config/wallpapermaison/vscode/workbench.html",
        Path.home() / ".config/wallpapermaison/vscode/workbench.html",
        Path.home() / "reseau/Perso/.local/share/vscode/resources/app/out/vs/code/electron-browser/workbench/workbench.html",
        Path.home() / ".local/share/vscode/resources/app/out/vs/code/electron-browser/workbench/workbench.html"
    ]

    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            with open(t, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    return True

def patch_preload() -> bool:
    orig_path = Path("/usr/apps/VSCode-linux-x64/resources/app/out/vs/base/parts/sandbox/electron-browser/preload.js")
    if not orig_path.exists():
        return False

    orig = orig_path.read_text(encoding="utf-8")
    target = "f={ipcRenderer:{"
    replacement = (
        'f={runCommand(cmd,...args){r.emit("vscode:runAction",{},{id:cmd,from:"button",args:args})},'
        'ipcRenderer:{emit(e,...n){r.emit(e,...n)},'
    )
    if target in orig:
        patched = orig.replace(target, replacement)
    else:
        patched = orig

    targets = [
        Path.home() / "reseau/Perso/.config/wallpapermaison/vscode/preload.js",
        Path.home() / ".config/wallpapermaison/vscode/preload.js",
        Path.home() / "reseau/Perso/.local/share/vscode/resources/app/out/vs/base/parts/sandbox/electron-browser/preload.js",
        Path.home() / ".local/share/vscode/resources/app/out/vs/base/parts/sandbox/electron-browser/preload.js"
    ]

    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            with open(t, "w", encoding="utf-8") as f:
                f.write(patched)
        except Exception:
            pass

    return True

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else None
    ok1 = patch_workbench(v_path)
    ok2 = patch_preload()
    sys.exit(0 if (ok1 and ok2) else 1)
