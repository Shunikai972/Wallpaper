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

# Enregistrement dans extensions.json pour que VS Code reconnaisse l'extension
if [ -n "$WP_DIR" ] && [ -f "$WP_DIR/scripts/register_extension.py" ]; then
    python3 "$WP_DIR/scripts/register_extension.py" 2>/dev/null || true
fi

# 4. Mise à jour et injection de workbench.html
if [ -n "$WP_DIR" ] && [ -f "$WP_DIR/scripts/patch_vscode_html.py" ]; then
    python3 "$WP_DIR/scripts/patch_vscode_html.py" 2>/dev/null || true
fi
P_HTML="$HOME/reseau/Perso/.config/wallpapermaison/vscode/workbench.html"
[ ! -f "$P_HTML" ] && P_HTML="$HOME/.config/wallpapermaison/vscode/workbench.html"
T_HTML="/usr/apps/VSCode-linux-x64/resources/app/out/vs/code/electron-browser/workbench/workbench.html"

# 5. Détection du binaire VS Code réel
VSCODE_BIN="/usr/apps/VSCode-linux-x64/code"
if [ ! -x "$VSCODE_BIN" ]; then
    for candidate in /usr/bin/code /usr/share/code/bin/code /usr/lib/code/code; do
        if [ -x "$candidate" ] && [ "$candidate" != "$HOME/.local/bin/code" ]; then
            VSCODE_BIN="$candidate"
            break
        fi
    done
fi

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
if command -v bwrap >/dev/null 2>&1 && [ -f "$P_HTML" ] && [ -f "$T_HTML" ] && [ -x "$VSCODE_BIN" ]; then
    BWRAP_ARGS="--dev-bind / / --ro-bind $P_HTML $T_HTML"
    if [ -n "$REAL_LIB" ] && [ -f "$REAL_LIB" ]; then
        if [ -f "/usr/lib64/libopenh264.so.8" ]; then
            BWRAP_ARGS="$BWRAP_ARGS --ro-bind $REAL_LIB /usr/lib64/libopenh264.so.8"
        fi
        if [ -f "/usr/lib64/libopenh264.so.2.6.0" ]; then
            BWRAP_ARGS="$BWRAP_ARGS --ro-bind $REAL_LIB /usr/lib64/libopenh264.so.2.6.0"
        fi
    fi
    exec bwrap $BWRAP_ARGS "$VSCODE_BIN" --extensions-dir /var/tmp/visual_extensions "$@"
elif [ -x "$VSCODE_BIN" ]; then
    exec "$VSCODE_BIN" --extensions-dir /var/tmp/visual_extensions "$@"
else
    echo "Erreur: Aucun binaire VS Code trouvé sur ce système." >&2
    exit 1
fi
