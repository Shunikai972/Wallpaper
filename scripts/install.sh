#!/usr/bin/env bash
# Universal installer entry point for local checkouts and curl | bash.
set -euo pipefail

APP_NAME="WallpaperMaison"
REPO_URL="https://github.com/Shunikai972/Wallpaper.git"

if [[ -z "${BASH_SOURCE[0]:-}" || "${BASH_SOURCE[0]}" == "bash" || \
      "${BASH_SOURCE[0]}" == "/dev/stdin" || "${BASH_SOURCE[0]}" == /dev/fd/* ]]; then
    printf 'Installation en ligne de %s\n' "$APP_NAME"
    if [[ -d "$HOME/reseau/Perso/Bureau" ]]; then
        TARGET_DIR="$HOME/reseau/Perso/Bureau/Wallpaper"
    elif [[ -d "$HOME/reseau/Perso" ]]; then
        TARGET_DIR="$HOME/reseau/Perso/Wallpaper"
    else
        TARGET_DIR="$HOME/Wallpaper"
    fi

    if [[ -d "$TARGET_DIR/.git" ]]; then
        git -C "$TARGET_DIR" pull --quiet || true
    else
        mkdir -p "$(dirname "$TARGET_DIR")"
        git clone "$REPO_URL" "$TARGET_DIR"
    fi
    SCRIPT_DIR="$TARGET_DIR"
else
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
fi

exec bash "$SCRIPT_DIR/scripts/setup.sh" "$@"
