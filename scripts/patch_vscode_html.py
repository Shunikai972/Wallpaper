#!/usr/bin/env python3
"""Génère la version patchée de workbench.html avec le fond d'écran vidéo et le bouton SUDO/Root."""

import os
import re
import sys
from pathlib import Path

def patch_workbench(video_path: str = None) -> bool:
    orig_path = Path("/usr/apps/VSCode-linux-x64/resources/app/out/vs/code/electron-browser/workbench/workbench.html")
    if not orig_path.exists():
        return False

    if not video_path:
        video_path = str(Path.home() / "reseau/Perso/Téléchargements/wallpaper.mp4")

    # Format vscode-file://
    if not video_path.startswith("vscode-file://"):
        resolved_path = Path(video_path).resolve()
        vsc_url = f"vscode-file://vscode-app{resolved_path}"
    else:
        vsc_url = video_path

    content = orig_path.read_text(encoding="utf-8")

    # 1. Mise à jour CSP
    content = content.replace("script-src", "script-src 'unsafe-inline'")
    content = content.replace("media-src", "media-src vscode-file: vscode-remote-resource: https: blob: data:")
    content = re.sub(r"require-trusted-types-for[^;]*;", "", content)
    content = re.sub(r"trusted-types[^;]*;", "", content)

    # 2. Nettoyage
    content = re.sub(r"<!-- live-wallpaper-start.*?<!-- live-wallpaper-end -->\n?", "", content, flags=re.DOTALL)

    # 3. Injection : Vidéo haute fidélité + Transparence Monaco + Bouton SUDO dans la Barre d'Activité
    patch_code = f"""<!-- live-wallpaper-start live-wallpaper.ver.1.0.10 -->
<style id="live-wallpaper-injected-style">
    /* Suppression des alertes de corruption */
    .notification-toast-container:has([aria-label*="corrupt"]) {{ display: none !important; }}

    /* Transparence complète de la zone d'édition (vide ou avec fichiers) */
    .monaco-workbench,
    .monaco-workbench .part.editor,
    .monaco-workbench .part.editor > .content,
    .monaco-workbench .part.editor .editor-group-container,
    .monaco-workbench .part.editor .editor-group-watermark,
    .monaco-workbench .part.editor .monaco-grid-view,
    .monaco-workbench .part.editor .monaco-grid-branch-node,
    .monaco-workbench .part.editor .empty,
    .monaco-workbench .part.editor .split-view-view {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    .monaco-workbench .part.editor .editor-group-watermark .letterpress {{
        opacity: 0.75 !important;
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

    /* Bouton flottant temporaire de secours si la barre tarde à s'afficher */
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
    var videoSrc = {repr(vsc_url)};

    function injectVideo() {{
        var existing = document.getElementById(LW_VIDEO_ID);
        if (existing) existing.remove();
        if (!videoSrc) return;

        var video = document.createElement('video');
        video.id = LW_VIDEO_ID;
        video.src = videoSrc;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.onerror = function(e) {{ console.error("Live Wallpaper decode error:", e); }};
        video.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;object-fit:cover;opacity:0.35;z-index:999;pointer-events:none;display:block;';
        document.body.appendChild(video);
        video.play().catch(function() {{}});
    }}

    function openSudoTerminal(e) {{
        if (e) {{ e.preventDefault(); e.stopPropagation(); }}
        console.log("[WallpaperMaison] Déclenchement du Terminal Sudo Root...");

        // 1. Déclenchement direct via runCommand (injecté dans preload.js)
        if (window.vscode && typeof window.vscode.runCommand === 'function') {{
            window.vscode.runCommand('liveWallpaper.openSudoTerminal');
            return;
        }}

        // 2. Déclenchement via ipcRenderer emit
        if (window.vscode && window.vscode.ipcRenderer && typeof window.vscode.ipcRenderer.emit === 'function') {{
            window.vscode.ipcRenderer.emit('vscode:runAction', {{}}, {{ id: 'liveWallpaper.openSudoTerminal', from: 'button', args: [] }});
            return;
        }}

        // 3. Déclenchement via DOM (item terminal ou bouton statusbar)
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

        // 4. Fallback runCommand terminal classique
        if (window.vscode && typeof window.vscode.runCommand === 'function') {{
            window.vscode.runCommand('workbench.action.terminal.new');
            return;
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

    function init() {{
        injectVideo();
        injectSudoButton();

        // Observation dynamique pour insérer dans la barre d'activité dès son apparition
        var observer = new MutationObserver(function() {{
            var act = document.querySelector('.part.activitybar ul.actions-container') ||
                      document.querySelector('.part.activitybar .composite-bar ul.actions-container') ||
                      document.querySelector('.activitybar .monaco-action-bar ul');
            if (act && (!document.getElementById('sudo-root-activity-action') || document.getElementById('vsc-sudo-action-btn-fallback'))) {{
                injectSudoButton();
            }}
        }});
        observer.observe(document.body, {{ childList: true, subtree: true }});
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
            if t.is_symlink():
                t.unlink()
            t.write_text(content, encoding="utf-8")
        except Exception:
            pass

    return True

def patch_preload() -> bool:
    orig_path = Path("/usr/apps/VSCode-linux-x64/resources/app/out/vs/base/parts/sandbox/electron-browser/preload.js")
    if not orig_path.exists():
        return False

    orig = orig_path.read_text(encoding="utf-8")
    target = "f={ipcRenderer:{"
    replacement = "f={runCommand(cmd,...args){r.emit(\"vscode:runAction\",{},{id:cmd,from:\"button\",args:args})},ipcRenderer:{emit(e,...n){r.emit(e,...n)},"
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
            if t.is_symlink():
                t.unlink()
            t.write_text(patched, encoding="utf-8")
        except Exception:
            pass

    return True

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else None
    ok1 = patch_workbench(v_path)
    ok2 = patch_preload()
    sys.exit(0 if (ok1 and ok2) else 1)

