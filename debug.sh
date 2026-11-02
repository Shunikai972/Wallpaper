#!/usr/bin/env bash
# Diagnostic en lecture seule ; seul le fichier de rapport est créé.
set -u
umask 077
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
report="$(mktemp "${HOME}/WallpaperMaison-debug-$(date +%Y%m%d-%H%M%S)-XXXXXX.log")" || exit 1
{
  printf 'WallpaperMaison : rapport de diagnostic\nDate : %s\nProjet : %s\n' "$(date -Is)" "$project_dir"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$project_dir" <<'PY'
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

home = Path.home()
project = Path(sys.argv[1])

def section(title):
    print('\n=== ' + title + ' ===', flush=True)

def describe(path):
    path = Path(path)
    try:
        if not path.exists():
            print(f'{path}: absent' + (' (lien cassé)' if path.is_symlink() else ''))
            return
        st = path.stat()
        print(f'{path}: présent, mode={st.st_mode & 0o777:o}, lecture={os.access(path, os.R_OK)}, écriture={os.access(path, os.W_OK)}, cible={path.resolve()}')
    except OSError as exc:
        print(f'{path}: erreur {exc}')

def run(label, command, timeout=5):
    print(f'\n{label}:', flush=True)
    try:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        print(f'code de retour: {result.returncode}\n{result.stdout[:6000]}')
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'indisponible: {exc}')

section('Système et session')
print('Système:', platform.platform())
for key in ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_DESKTOP', 'XDG_SESSION_ID', 'DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR'):
    print(f'{key}={os.environ.get(key, "(absent)")}')
for line in Path('/etc/os-release').read_text(errors='replace').splitlines() if Path('/etc/os-release').is_file() else []:
    if line.startswith(('ID=', 'VERSION_ID=', 'PRETTY_NAME=')):
        print(line)

section('Commandes et dépendances')
for name in ('code', 'code-insiders', 'bwrap', 'flatpak', 'python3', 'ffmpeg', 'mpv', 'gsettings', 'gnome-extensions'):
    print(f'{name}: {shutil.which(name) or "introuvable"}')
code = shutil.which('code')
if code:
    describe(code)
    print('Version de code : voir les fichiers package.json détectés ci-dessous (la commande code ne sera pas exécutée).')
if shutil.which('bwrap'):
    run('Test de bubblewrap', ['bwrap', '--dev-bind', '/', '/', 'true'])
if shutil.which('flatpak'):
    try:
        apps = subprocess.run(['flatpak', 'list', '--app', '--columns=application'], text=True, capture_output=True, timeout=5)
        matches = [line for line in apps.stdout.splitlines() if 'visualstudio' in line.lower() or 'vscode' in line.lower() or 'vscodium' in line.lower()]
        print('Applications VS Code / VSCodium Flatpak:', ', '.join(matches) or '(aucune détectée)')
        if apps.returncode:
            print('flatpak list code de retour:', apps.returncode)
    except (OSError, subprocess.SubprocessError) as exc:
        print('flatpak list indisponible:', exc)
venv = project / '.venv/bin/python'
if venv.is_file():
    run('Imports Python du projet', [str(venv), '-c', 'import sys; print(sys.version); import PIL, webview; print("Pillow et pywebview : OK")'])
else:
    print(f'Environnement virtuel absent: {venv}')

section('Installation et raccourcis')
for path in (project / 'scripts/install.sh', project / 'scripts/code-launcher.sh', home / '.local/bin/code', home / '.local/bin/wallpapermaison-code', home / '.local/bin/wallpapermaison-session-start', home / '.config/wallpapermaison/project-path', home / '.config/autostart/wallpapermaison.desktop', home / '.local/share/applications/wallpapermaison-code.desktop', home / '.local/share/applications/code.desktop', home / '.local/share/applications/vscode.desktop'):
    describe(path)
    if path.name.endswith('.desktop') or path.name == 'project-path':
        try:
            for line in path.read_text(errors='replace').splitlines():
                if path.name == 'project-path' or line.startswith(('Name=', 'Exec=', 'Hidden=', 'X-GNOME-Autostart-enabled=')):
                    print('  ', line)
        except OSError:
            pass
legacy = home / '.bashrc.d/wallpapermaison.sh'
try:
    print('Ancien alias code présent:', any(re.search(r'^\s*alias\s+code=', line) for line in legacy.read_text(errors='replace').splitlines()))
except OSError:
    print('Ancien fichier shell absent')

section('VS Code et injection')
roots = [Path('/usr/share/code'), Path('/usr/lib/code'), Path('/opt/visual-studio-code'), Path('/usr/apps/VSCode-linux-x64')]
if code:
    binary = Path(code).resolve()
    roots.extend(binary.parents)
htmls = []
for root in roots:
    for layout in ('electron-browser', 'electron-sandbox'):
        html = root / 'resources/app/out/vs/code' / layout / 'workbench/workbench.html'
        if html.is_file() and html not in htmls:
            htmls.append(html)
            describe(html)
            try:
                package = json.loads((root / 'resources/app/package.json').read_text())
                print('  Version VS Code:', package.get('version', '(absente)'))
            except (OSError, ValueError):
                pass
if not htmls:
    print('workbench.html natif introuvable dans les chemins recherchés')
overlay = home / '.config/wallpapermaison/vscode/workbench'
for item in (overlay / 'workbench.html', overlay / 'workbench.js'):
    describe(item)
try:
    text = (overlay / 'workbench.html').read_text(errors='replace')
    print('Marqueurs injection:', 'live-wallpaper-start' in text, '__applyWallpaperMaisonMedia' in text)
except OSError:
    pass
ext = home / '.vscode/extensions/budicuy.live-wallpaper-99.0.0'
for item in (ext, ext / 'package.json', ext / 'live_state.json', ext / 'wallpaper-media', home / '.vscode/extensions/extensions.json'):
    describe(item)
try:
    registry = json.loads((home / '.vscode/extensions/extensions.json').read_text())
    entries = [e for e in registry if isinstance(e, dict) and e.get('identifier', {}).get('id', '').lower() == 'budicuy.live-wallpaper']
    print('Entrées de registre Live Wallpaper:', json.dumps(entries, ensure_ascii=False))
except (OSError, ValueError, TypeError, AttributeError) as exc:
    print('Registre illisible:', exc)

section('État de synchronisation')
for item in (home / '.config/wallpapermaison/current_wallpaper.json', ext / 'live_state.json'):
    try:
        data = json.loads(item.read_text())
        print(item, json.dumps({k: data.get(k) for k in ('path', 'media_type', 'source', 'timestamp')}, ensure_ascii=False))
        media = data.get('path', '')
        if media and not str(media).startswith(('http://', 'https://')):
            describe(media)
    except (OSError, ValueError, TypeError) as exc:
        print(f'{item}: {exc}')
info = Path(os.environ.get('WALLPAPERMAISON_VSCODE_MEDIA_INFO', str(Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/wallpapermaison-{os.getuid()}')) / 'wallpapermaison-vscode-media.json')))
try:
    data = json.loads(info.read_text())
    base = data.get('base_url', '')
    parsed = urlsplit(base)
    print('Serveur média:', base, 'pid:', data.get('pid'))
    if parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and parsed.port and not parsed.username and not parsed.path:
        with build_opener(ProxyHandler({})).open(base + '/health', timeout=2) as response:
            print('Santé serveur HTTP:', response.status)
    else:
        print('Adresse serveur invalide, test ignoré')
except (OSError, ValueError, TypeError) as exc:
    print('Serveur média indisponible:', exc)

section('Processus et montages VS Code')
proc = Path('/proc')
for pid in proc.iterdir():
    if not pid.name.isdigit():
        continue
    try:
        if pid.stat().st_uid != os.getuid():
            continue
        name = (pid / 'comm').read_text().strip()
        if name.lower() not in ('code', 'code-insiders', 'wallpapermaison'):
            continue
        print(f'PID={pid.name} nom={name}')
        for line in (pid / 'mountinfo').read_text(errors='replace').splitlines():
            if 'wallpapermaison/vscode/workbench' in line:
                print('  montage:', line)
    except (OSError, PermissionError):
        pass

section('Journaux récents de WallpaperMaison')
log_dir = home / '.cache/wallpapermaison/logs'
for name in ('session-start.log', 'autostart_daemon.log', 'wallpapermaison.log', 'vscode-media-server.log'):
    path = log_dir / name
    print(f'\n--- {path} (80 dernières lignes) ---')
    try:
        with path.open('rb') as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 65536))
            print('\n'.join(f.read().decode('utf-8', 'replace').splitlines()[-80:]))
    except OSError as exc:
        print(exc)
print('\nFin du rapport.')
PY
  else
    printf 'python3 est introuvable : impossible de réaliser le diagnostic complet.\n'
  fi
} > "$report" 2>&1
printf 'Rapport créé : %s\n' "$report"
printf 'Il peut contenir des noms et chemins de fichiers ainsi que des extraits des journaux WallpaperMaison : vérifiez-le avant de le partager.\n'
