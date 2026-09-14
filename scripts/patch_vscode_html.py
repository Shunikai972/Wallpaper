#!/usr/bin/env python3
"""Génère la version patchée de workbench.html avec fond vidéo réactif, Monaco transparent et lecture ininterrompue."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

def detect_current_video_path(preferred_path: str = None) -> str:
    """Détecte avec certitude le fond d'écran vidéo actuellement actif sur le bureau."""
    if preferred_path and Path(preferred_path).exists():
        return str(Path(preferred_path).resolve())

    # 1. Vérification GSettings Hanabi
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

    # 4. Premier MP4 disponible
    for dl_dir in [Path.home() / "reseau/Perso/Téléchargements", Path.home() / "Téléchargements"]:
        if dl_dir.exists():
            mp4s = list(dl_dir.glob("*.mp4"))
            if mp4s:
                return str(mp4s[0].resolve())

    return str(Path.home() / "reseau/Perso/Téléchargements/wallpaper.mp4")

def update_live_state(video_path: str, media_type: str = "video") -> None:
    """Met à jour les fichiers live_state (.json et .js) dans les extensions autorisées par VS Code."""
    import time
    resolved = str(Path(video_path).resolve()) if video_path else ""
    st_data = {
        "path": resolved,
        "media_type": media_type,
        "source": "desktop",
        "timestamp": time.time()
    }
    js_code = f""";(function() {{
    var p = {repr(resolved)};
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
            with open(t_dir / "live_state.json", "w", encoding="utf-8") as f:
                json.dump(st_data, f, indent=2)
            with open(t_dir / "live_state.js", "w", encoding="utf-8") as f:
                f.write(js_code)
        except Exception:
            pass

def patch_workbench(video_path: str = None) -> bool:
    orig_path = Path("/usr/apps/VSCode-linux-x64/resources/app/out/vs/code/electron-browser/workbench/workbench.html")
    if not orig_path.exists():
        return False

    resolved_video_path = detect_current_video_path(video_path)

    # Format vscode-file:// avec quote pour préserver les accents (ex: Téléchargements -> T%C3%A9l%C3%A9chargements)
    quoted_path = quote(str(resolved_video_path), safe="/:@!$&'()*+,;=-_.~")
    vsc_url = f"vscode-file://vscode-app{quoted_path}"

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
            sf.parent.mkdir(parents=True, exist_ok=True)
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(st_data, f, indent=2)
        except Exception:
            pass

    update_live_state(resolved_video_path, "video")

    content = orig_path.read_text(encoding="utf-8")

    # 1. Mise à jour CSP pour autoriser les médias locaux, scripts d'extension et connexions locales
    content = content.replace("script-src", "script-src 'unsafe-inline' vscode-file: http:")
    content = content.replace("media-src", "media-src 'self' vscode-file: vscode-remote-resource: https: blob: data:")
    content = content.replace("img-src", "img-src 'self' vscode-file: vscode-remote-resource: https: blob: data:")
    if "connect-src" in content:
        content = content.replace("connect-src", "connect-src 'self' vscode-file: vscode-remote-resource: https: ws: http:")
    else:
        content = content.replace(
            "default-src\n\t\t\t\t\t'none'\n\t\t\t\t;",
            "default-src 'none';\n\t\t\t\tconnect-src 'self' vscode-file: vscode-remote-resource: https: ws: http:;"
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

    /* Vidéo ou Image de fond : superposition transparente permanente */
    #live-wallpaper-bg-video, #live-wallpaper-bg-img {{
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
    var currentRawPath = {repr(str(resolved_video_path))};

    function isVideoSrc(src) {{
        if (!src) return true;
        var clean = src.split('?')[0].toLowerCase();
        return clean.endsWith('.mp4') || clean.endsWith('.webm') || clean.endsWith('.mkv') || !clean.match(/\\.(png|jpe?g|webp|gif|bmp|svg)$/);
    }}

    function toVscUrl(p) {{
        if (!p) return '';
        if (p.startsWith('vscode-file://')) return p;
        var clean = p.startsWith('file://') ? p.slice(7) : p;
        return 'vscode-file://vscode-app' + encodeURI(clean);
    }}

    function applyMedia(rawSrc) {{
        if (!rawSrc) return;
        var src = toVscUrl(rawSrc);
        var oldVid = document.getElementById(LW_VIDEO_ID);
        var oldImg = document.getElementById(LW_IMG_ID);

        if (currentRawPath === rawSrc && (oldVid || oldImg)) {{
            if (oldVid && oldVid.paused) {{
                oldVid.play().catch(function() {{}});
            }}
            return;
        }}

        currentMediaSrc = src;
        currentRawPath = rawSrc;

        if (oldVid) oldVid.remove();
        if (oldImg) oldImg.remove();

        var commonStyle = [
            'position: fixed !important',
            'top: 0 !important',
            'left: 0 !important',
            'width: 100vw !important',
            'height: 100vh !important',
            'object-fit: cover !important',
            'opacity: 0.35 !important',
            'z-index: 999 !important',
            'pointer-events: none !important',
            'display: block !important'
        ].join(';');

        if (isVideoSrc(src)) {{
            var video = document.createElement('video');
            video.id = LW_VIDEO_ID;
            video.muted = true;
            video.defaultMuted = true;
            video.autoplay = true;
            video.loop = true;
            video.playsInline = true;
            video.preload = 'auto';

            video.setAttribute('muted', '');
            video.setAttribute('autoplay', '');
            video.setAttribute('loop', '');
            video.setAttribute('playsinline', '');
            video.setAttribute('webkit-playsinline', '');

            video.style.cssText = commonStyle;

            video.oncanplay = function() {{
                if (video.paused) video.play().catch(function() {{}});
            }};
            video.onloadeddata = function() {{
                if (video.paused) video.play().catch(function() {{}});
            }};
            video.onended = function() {{
                video.currentTime = 0;
                video.play().catch(function() {{}});
            }};
            video.onerror = function(e) {{
                console.warn("[WallpaperMaison] Erreur lecture vidéo:", e);
            }};

            video.src = src;
            document.body.appendChild(video);

            video.play().catch(function() {{}});
        }} else {{
            var img = document.createElement('img');
            img.id = LW_IMG_ID;
            img.src = src;
            img.style.cssText = commonStyle;
            document.body.appendChild(img);
        }}
    }}

    window.__applyWallpaperMaisonMedia = applyMedia;

    function ensureMedia() {{
        var vid = document.getElementById(LW_VIDEO_ID);
        var img = document.getElementById(LW_IMG_ID);
        if (!vid && !img) {{
            if (currentRawPath) applyMedia(currentRawPath);
            else if (currentMediaSrc) applyMedia(currentMediaSrc);
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
            var target = jsonUrls[0] + '?_t=' + Date.now();
            fetch(target, {{ cache: 'no-store' }})
                .then(function(res) {{
                    if (!res.ok) throw new Error('status ' + res.status);
                    return res.json();
                }})
                .then(function(data) {{
                    if (data && data.path && data.path !== currentRawPath) {{
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
                    s.src = scriptUrls[0] + '?_t=' + Date.now();
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

    function init() {{
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

        window.addEventListener('focus', ensureMedia);
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
