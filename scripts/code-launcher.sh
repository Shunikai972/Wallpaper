#!/usr/bin/env bash
# WallpaperMaison VS Code launcher. The system's `code` remains untouched.
set -u
project="${WALLPAPERMAISON_DIR:-}"
for config in "$HOME/.config/wallpapermaison/project-path" "$HOME/reseau/Perso/.config/wallpapermaison/project-path"; do
    if [ -z "$project" ] && [ -r "$config" ]; then IFS= read -r project < "$config" || true; fi
done
for candidate in "$HOME/Wallpaper" "$HOME/reseau/Perso/Bureau/Wallpaper"; do
    if [ -z "$project" ] && [ -f "$candidate/scripts/patch_vscode_html.py" ]; then project="$candidate"; fi
done

# Skip our legacy wrapper and discover installations from PATH as well as common layouts.
code_bin="${WALLPAPERMAISON_CODE_BIN:-}"
if [ -z "$code_bin" ]; then
    old_ifs=$IFS; IFS=:
    for dir in $PATH; do
        [ -n "$dir" ] || dir=.
        candidate="$dir/code"
        if [ -x "$candidate" ]; then
            if [ "$candidate" = "$HOME/.local/bin/code" ] && grep -q 'Visual Studio Code Portable Launcher avec Live Wallpaper' "$candidate" 2>/dev/null; then continue; fi
            code_bin="$candidate"; break
        fi
    done
    IFS=$old_ifs
fi
if [ -z "$code_bin" ]; then
    for candidate in /usr/bin/code /usr/share/code/bin/code /usr/apps/VSCode-linux-x64/bin/code /opt/visual-studio-code/bin/code; do
        if [ -x "$candidate" ]; then code_bin="$candidate"; break; fi
    done
fi
if [ -z "$code_bin" ] || [ ! -x "$code_bin" ]; then
    echo "WallpaperMaison : VS Code introuvable. Installez VS Code ou définissez WALLPAPERMAISON_CODE_BIN." >&2
    exit 1
fi
# CLI commands must retain the distribution's original behavior.
for arg in "$@"; do
    case "$arg" in --version|-v|--list-extensions|--install-extension|--uninstall-extension|--status|--help|-h) exec "$code_bin" "$@";; esac
done

resolved="$(readlink -f "$code_bin")"
search_dir="$(dirname "$resolved")"
html=""
while [ "$search_dir" != / ]; do
    for layout in electron-browser electron-sandbox; do
        candidate="$search_dir/resources/app/out/vs/code/$layout/workbench/workbench.html"
        if [ -f "$candidate" ]; then html="$candidate"; break; fi
    done
    [ -n "$html" ] && break
    search_dir="$(dirname "$search_dir")"
done
if [ -n "$html" ] && [ -f "$project/scripts/patch_vscode_html.py" ] && command -v bwrap >/dev/null 2>&1 && bwrap --dev-bind / / true >/dev/null 2>&1; then
    export WALLPAPERMAISON_VSCODE_HTML="$html"
    if python3 "$project/scripts/patch_vscode_html.py"; then
        overlay="$HOME/.config/wallpapermaison/vscode/workbench"
        if [ -f "$overlay/workbench.html" ] && [ -f "$overlay/workbench.js" ]; then
            exec bwrap --dev-bind / / --ro-bind "$overlay" "$(dirname "$html")" "$code_bin" "$@"
        fi
    fi
fi
echo "WallpaperMaison : injection VS Code indisponible (installation non détectée ou bubblewrap inutilisable). VS Code démarre normalement." >&2
exec "$code_bin" "$@"
