#!/bin/bash
# ==============================================================================
# Visual Studio Code Portable Launcher avec Live Wallpaper et Sudo Root Terminal
# ==============================================================================

# 1. Localisation dynamique du projet WallpaperMaison
WP_DIR=""
for candidate in \
    "$HOME/reseau/Perso/Bureau/Wallpaper" \
    "$HOME/Bureau/Wallpaper" \
    "$HOME/Wallpaper" \
    "/var/home/$USER/reseau/Perso/Bureau/Wallpaper"; do
    if [ -d "$candidate" ] && [ -f "$candidate/scripts/patch_vscode_html.py" ]; then
        WP_DIR="$candidate"
        break
    fi
done

# 2. Déploiement / mise à jour automatique de root-shell
if [ -n "$WP_DIR" ] && [ -f "$WP_DIR/scripts/root-shell" ]; then
    mkdir -p "$HOME/.local/bin"
    cp -f "$WP_DIR/scripts/root-shell" "$HOME/.local/bin/root-shell" 2>/dev/null || true
    chmod +x "$HOME/.local/bin/root-shell" 2>/dev/null || true
    if [ -d "$HOME/reseau/Perso/.local/bin" ]; then
        cp -f "$WP_DIR/scripts/root-shell" "$HOME/reseau/Perso/.local/bin/root-shell" 2>/dev/null || true
        chmod +x "$HOME/reseau/Perso/.local/bin/root-shell" 2>/dev/null || true
    fi
fi

# 2.5 Déploiement et synchronisation du codec Cisco OpenH264 (H.264 matériel et Chromium)
REAL_LIB=""
if [ -f "$HOME/.local/lib/libopenh264.so.8" ]; then
    REAL_LIB="$HOME/.local/lib/libopenh264.so.8"
elif [ -f "$HOME/reseau/Perso/.local/lib/libopenh264.so.8" ]; then
    mkdir -p "$HOME/.local/lib" 2>/dev/null || true
    cp -af "$HOME/reseau/Perso/.local/lib"/libopenh264* "$HOME/.local/lib/" 2>/dev/null || true
    REAL_LIB="$HOME/.local/lib/libopenh264.so.8"
fi
export LD_LIBRARY_PATH="$HOME/.local/lib:$HOME/reseau/Perso/.local/lib:${LD_LIBRARY_PATH}"

# 3. Synchronisation automatique des extensions (locale + tmp)
mkdir -p "$HOME/.vscode/extensions" /var/tmp/visual_extensions 2>/dev/null || true

# Nettoyage des versions tierces marketplace (1.1.*) et de l'obsolescence forcée
rm -rf /var/tmp/visual_extensions/budicuy.live-wallpaper-1.1.* 2>/dev/null || true
rm -rf /var/tmp/visual_extensions/budicuy.live-wallpaper-1.0.* 2>/dev/null || true
rm -rf "$HOME/.vscode/extensions"/budicuy.live-wallpaper-1.1.* 2>/dev/null || true
rm -rf "$HOME/.vscode/extensions"/budicuy.live-wallpaper-1.0.* 2>/dev/null || true
rm -rf "$HOME/reseau/Perso/.vscode/extensions"/budicuy.live-wallpaper-1.1.* 2>/dev/null || true
rm -rf "$HOME/reseau/Perso/.vscode/extensions"/budicuy.live-wallpaper-1.0.* 2>/dev/null || true

if [ -f /var/tmp/visual_extensions/.obsolete ]; then
    sed -i 's/"budicuy\.live-wallpaper-[^"]*":true,//g; s/,"budicuy\.live-wallpaper-[^"]*":true//g; s/"budicuy\.live-wallpaper-[^"]*":true//g' /var/tmp/visual_extensions/.obsolete 2>/dev/null || true
fi

# Déploiement de notre extension personnalisée (version 99.0.0)
if [ -n "$WP_DIR" ] && [ -d "$WP_DIR/vscode-extension" ]; then
    export WALLPAPERMAISON_DIR="$WP_DIR"
    export WALLPAPERMAISON_VSCODE_EXT_DIR="/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0"
    mkdir -p "$HOME/.vscode/extensions/budicuy.live-wallpaper-99.0.0"
    cp -rf "$WP_DIR/vscode-extension"/* "$HOME/.vscode/extensions/budicuy.live-wallpaper-99.0.0/" 2>/dev/null || true
    if [ -d "$HOME/reseau/Perso/.vscode/extensions" ]; then
        mkdir -p "$HOME/reseau/Perso/.vscode/extensions/budicuy.live-wallpaper-99.0.0"
        cp -rf "$WP_DIR/vscode-extension"/* "$HOME/reseau/Perso/.vscode/extensions/budicuy.live-wallpaper-99.0.0/" 2>/dev/null || true
    fi
    mkdir -p /var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0
    cp -rf "$WP_DIR/vscode-extension"/* /var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0/ 2>/dev/null || true
fi

# Synchroniser toutes les extensions vers /var/tmp/visual_extensions
if [ -d "$HOME/reseau/Perso/.vscode/extensions" ]; then
    cp -rf "$HOME/reseau/Perso/.vscode/extensions/"* /var/tmp/visual_extensions/ 2>/dev/null || true
elif [ -d "$HOME/.vscode/extensions" ]; then
    cp -rf "$HOME/.vscode/extensions/"* /var/tmp/visual_extensions/ 2>/dev/null || true
fi

# The persistent extension directory may contain an older copy. Keep the
# workspace build authoritative after synchronizing third-party extensions.
if [ -n "$WP_DIR" ] && [ -d "$WP_DIR/vscode-extension" ]; then
    mkdir -p /var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0
    cp -rf "$WP_DIR/vscode-extension"/* /var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0/ 2>/dev/null || true
fi

# Enregistrement dans extensions.json pour que VS Code reconnaisse l'extension
if [ -n "$WP_DIR" ] && [ -f "$WP_DIR/scripts/register_extension.py" ]; then
    python3 "$WP_DIR/scripts/register_extension.py" 2>/dev/null || true
fi

# 4. Détection du binaire et du workbench de VS Code
VSCODE_BIN="/usr/apps/VSCode-linux-x64/code"
if [ ! -x "$VSCODE_BIN" ]; then
    for candidate in /usr/bin/code /usr/share/code/bin/code /usr/share/code/code /usr/lib/code/code /usr/lib/code/bin/code; do
        if [ -x "$candidate" ] && [ "$candidate" != "$HOME/.local/bin/code" ]; then
            VSCODE_BIN="$candidate"
            break
        fi
    done
fi

T_HTML=""
if [ -x "$VSCODE_BIN" ]; then
    VSCODE_BIN="$(readlink -f "$VSCODE_BIN" 2>/dev/null || echo "$VSCODE_BIN")"
    search_dir="$(dirname "$VSCODE_BIN")"
    while [ -n "$search_dir" ] && [ "$search_dir" != "/" ]; do
        for layout in electron-browser electron-sandbox; do
            candidate="$search_dir/resources/app/out/vs/code/$layout/workbench/workbench.html"
            if [ -f "$candidate" ]; then
                T_HTML="$candidate"
                break 2
            fi
        done
        search_dir="$(dirname "$search_dir")"
    done
fi

# 5. Mise à jour et injection du workbench réellement utilisé
if [ -n "$T_HTML" ]; then
    export WALLPAPERMAISON_VSCODE_HTML="$T_HTML"
fi
PATCH_OK=0
if [ -n "$WP_DIR" ] && [ -f "$WP_DIR/scripts/patch_vscode_html.py" ]; then
    if python3 "$WP_DIR/scripts/patch_vscode_html.py"; then
        PATCH_OK=1
    else
        echo "WallpaperMaison: VS Code workbench patch generation failed; starting VS Code without the wallpaper overlay." >&2
    fi
fi
P_HTML_DIR="$HOME/reseau/Perso/.config/wallpapermaison/vscode/workbench"
if [ ! -f "$P_HTML_DIR/workbench.html" ] || [ ! -f "$P_HTML_DIR/workbench.js" ]; then
    P_HTML_DIR="$HOME/.config/wallpapermaison/vscode/workbench"
fi
P_HTML="$HOME/reseau/Perso/.config/wallpapermaison/vscode/workbench.html"
[ ! -f "$P_HTML" ] && P_HTML="$HOME/.config/wallpapermaison/vscode/workbench.html"

# 6. Exécution des commandes CLI pures via le runtime Node de VS Code
for arg in "$@"; do
    case "$arg" in
        --version|-v|--list-extensions|--install-extension|--uninstall-extension|--status|--help|-h)
            if [ -x "/usr/apps/VSCode-linux-x64/bin/code" ]; then
                exec /usr/apps/VSCode-linux-x64/bin/code --extensions-dir /var/tmp/visual_extensions "$@"
            elif [ -f "/usr/apps/VSCode-linux-x64/resources/app/out/cli.js" ]; then
                exec env ELECTRON_RUN_AS_NODE=1 "$VSCODE_BIN" /usr/apps/VSCode-linux-x64/resources/app/out/cli.js --extensions-dir /var/tmp/visual_extensions "$@"
            fi
            ;;
    esac
done

# 7. Lancement GUI avec bwrap pour injecter le fond d'écran et l'action sudo
if command -v bwrap >/dev/null 2>&1 && [ -f "$T_HTML" ] && [ -x "$VSCODE_BIN" ] && [ "$PATCH_OK" -eq 1 ]; then
    BWRAP_ARGS=(--dev-bind / /)
    if [ -f "$P_HTML_DIR/workbench.html" ] && [ -f "$P_HTML_DIR/workbench.js" ]; then
        BWRAP_ARGS+=(--ro-bind "$P_HTML_DIR" "$(dirname "$T_HTML")")
    elif [ -f "$P_HTML" ]; then
        BWRAP_ARGS+=(--ro-bind "$P_HTML" "$T_HTML")
    else
        exec "$VSCODE_BIN" --extensions-dir /var/tmp/visual_extensions "$@"
    fi
    if [ -n "$REAL_LIB" ] && [ -f "$REAL_LIB" ]; then
        if [ -f "/usr/lib64/libopenh264.so.8" ]; then
            BWRAP_ARGS+=(--ro-bind "$REAL_LIB" /usr/lib64/libopenh264.so.8)
        fi
        if [ -f "/usr/lib64/libopenh264.so.2.6.0" ]; then
            BWRAP_ARGS+=(--ro-bind "$REAL_LIB" /usr/lib64/libopenh264.so.2.6.0)
        fi
    fi
    exec bwrap "${BWRAP_ARGS[@]}" "$VSCODE_BIN" --extensions-dir /var/tmp/visual_extensions "$@"
elif [ -x "$VSCODE_BIN" ]; then
    exec "$VSCODE_BIN" --extensions-dir /var/tmp/visual_extensions "$@"
else
    echo "Erreur: Aucun binaire VS Code trouvé sur ce système." >&2
    exit 1
fi
