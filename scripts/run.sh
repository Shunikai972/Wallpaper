#!/usr/bin/env bash
# ==============================================================================
# WallpaperMaison - Script de lancement intelligent et portable
# Compatible Wayland/X11, Fedora Silverblue/Workstation, stockage persistant NFS
# ==============================================================================
set -e

# Résolution dynamique et portable du répertoire du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Importer les valeurs de la session graphique si systemd a lancé le service
# avant le fichier XDG Autostart. Le verrou est propre à l'écran/session : une
# seconde connexion au même compte peut ainsi démarrer son propre renderer.
if command -v systemctl >/dev/null 2>&1; then
    for env_key in WAYLAND_DISPLAY DISPLAY XDG_SESSION_ID XDG_SESSION_TYPE XDG_CURRENT_DESKTOP DBUS_SESSION_BUS_ADDRESS; do
        if [ -z "${!env_key:-}" ]; then
            env_value="$(systemctl --user show-environment 2>/dev/null | sed -n "s/^${env_key}=//p" | head -n 1 || true)"
            if [ -n "$env_value" ]; then
                export "${env_key}=${env_value}"
            fi
        fi
    done
fi

SESSION_SCOPE="${WALLPAPERMAISON_SESSION_SCOPE:-${XDG_SESSION_ID:-${WAYLAND_DISPLAY:-${DISPLAY:-user}}}}"
SESSION_SCOPE="$(printf '%s' "$SESSION_SCOPE" | tr -c 'A-Za-z0-9_.-' '_')"
XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if command -v flock >/dev/null 2>&1 && [ -d "$XDG_RUNTIME_DIR" ]; then
    exec 9>"${XDG_RUNTIME_DIR}/wallpapermaison_bootstrap_${SESSION_SCOPE}.lock"
    if ! flock -n 9; then
        exit 0
    fi
fi
export WALLPAPERMAISON_SESSION_SCOPE="$SESSION_SCOPE"

# Détection et auto-guérison du stockage persistant réseau (IUT NFS reseau/Perso)
if [ -d "${HOME}/reseau/Perso" ]; then
    mkdir -p "${HOME}/.config" "${HOME}/.local/share" "${HOME}/.cache"
    P_CONFIG="${HOME}/reseau/Perso/.config/wallpapermaison"
    P_DATA="${HOME}/reseau/Perso/.local/share/wallpapermaison"
    P_CACHE="${HOME}/reseau/Perso/.cache/wallpapermaison"

    mkdir -p "${P_CONFIG}" "${P_DATA}" "${P_CACHE}/thumbnails" "${P_CACHE}/processed" "${P_CACHE}/logs"

    [ ! -e "${HOME}/.config/wallpapermaison" ] && ln -sfn "${P_CONFIG}" "${HOME}/.config/wallpapermaison" 2>/dev/null || true
    [ ! -e "${HOME}/.local/share/wallpapermaison" ] && ln -sfn "${P_DATA}" "${HOME}/.local/share/wallpapermaison" 2>/dev/null || true
    [ ! -e "${HOME}/.cache/wallpapermaison" ] && ln -sfn "${P_CACHE}" "${HOME}/.cache/wallpapermaison" 2>/dev/null || true
fi

# Auto-guérison et déploiement des codecs vidéo (OpenH264 officiel Cisco pour décodage H.264)
LIB_PERSIST="${HOME}/reseau/Perso/.local/lib"
LIB_LOCAL="${HOME}/.local/lib"
mkdir -p "${LIB_LOCAL}" "${LIB_PERSIST}" 2>/dev/null || true
H264_SRC=""
for cand in \
    "${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io/lib/libopenh264.so.8" \
    "${SCRIPT_DIR}/lib/libopenh264.so.8" \
    "${LIB_PERSIST}/libopenh264.so.8" \
    "${LIB_LOCAL}/libopenh264.so.8"; do
    if [ -f "$cand" ]; then
        H264_SRC="$cand"
        break
    fi
done

if [ -z "$H264_SRC" ]; then
    if command -v curl &>/dev/null && command -v bzip2 &>/dev/null; then
        mkdir -p "${LIB_LOCAL}" "${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io/lib" 2>/dev/null || true
        curl -sL "http://ciscobinary.openh264.org/libopenh264-2.6.0-linux64.8.so.bz2" | bzip2 -d > "${LIB_LOCAL}/libopenh264.so.8" 2>/dev/null || true
        if [ -s "${LIB_LOCAL}/libopenh264.so.8" ]; then
            chmod 755 "${LIB_LOCAL}/libopenh264.so.8"
            H264_SRC="${LIB_LOCAL}/libopenh264.so.8"
        fi
    fi
fi

if [ -n "$H264_SRC" ] && [ -f "$H264_SRC" ]; then
    for target_dir in "${LIB_LOCAL}" "${LIB_PERSIST}" "${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io/lib"; do
        mkdir -p "$target_dir" 2>/dev/null || true
        if [ ! -f "$target_dir/libopenh264.so.8" ]; then
            cp -f "$H264_SRC" "$target_dir/libopenh264.so.8" 2>/dev/null || true
        fi
        ln -sf "libopenh264.so.8" "$target_dir/libopenh264.so.2.6.0" 2>/dev/null || true
        ln -sf "libopenh264.so.8" "$target_dir/libopenh264.so" 2>/dev/null || true
        chmod 755 "$target_dir"/libopenh264* 2>/dev/null || true
    done
fi

# Auto-guérison et déploiement de root-shell, lanceur VS Code et autostart
mkdir -p "${HOME}/.local/bin" "${HOME}/.local/share/applications" "${HOME}/.config/autostart" 2>/dev/null || true
if [ -f "${SCRIPT_DIR}/scripts/session-start.sh" ]; then
    cp -f "${SCRIPT_DIR}/scripts/session-start.sh" "${HOME}/.local/bin/wallpapermaison-session-start" 2>/dev/null || true
    chmod +x "${HOME}/.local/bin/wallpapermaison-session-start" 2>/dev/null || true
fi
if [ ! -f "${HOME}/.config/autostart/wallpapermaison.desktop" ] && [ -f "${SCRIPT_DIR}/scripts/autostart.desktop" ]; then
    cp -f "${SCRIPT_DIR}/scripts/autostart.desktop" "${HOME}/.config/autostart/wallpapermaison.desktop" 2>/dev/null || true
fi
if [ -f "${SCRIPT_DIR}/scripts/root-shell" ]; then
    cp -f "${SCRIPT_DIR}/scripts/root-shell" "${HOME}/.local/bin/root-shell" 2>/dev/null || true
    chmod +x "${HOME}/.local/bin/root-shell" 2>/dev/null || true
fi
if [ -f "${SCRIPT_DIR}/scripts/code-launcher.sh" ]; then
    cp -f "${SCRIPT_DIR}/scripts/code-launcher.sh" "${HOME}/.local/bin/code" 2>/dev/null || true
    chmod +x "${HOME}/.local/bin/code" 2>/dev/null || true
fi
if [ ! -f "${HOME}/.local/share/applications/vscode.desktop" ]; then
    cat << 'EOF_VSC' > "${HOME}/.local/share/applications/vscode.desktop"
[Desktop Entry]
Name=Visual Studio Code
Comment=Code Editing. Redefined.
GenericName=Text Editor
Exec=bash -c 'exec "$HOME/.local/bin/code" %F'
Icon=vscode
Type=Application
StartupNotify=false
StartupWMClass=code
Categories=TextEditor;Development;IDE;
MimeType=text/plain;inode/directory;application/x-code-workspace;
Keywords=vscode;
EOF_VSC
fi

# Synchronisation automatique de l'extension VS Code (locale + tmp)
mkdir -p "${HOME}/.vscode/extensions" /var/tmp/visual_extensions 2>/dev/null || true
if [ -d "${SCRIPT_DIR}/vscode-extension" ]; then
    rm -rf "${HOME}/.vscode/extensions/budicuy.live-wallpaper-1.0.9" /var/tmp/visual_extensions/budicuy.live-wallpaper-1.0.9 2>/dev/null || true
    mkdir -p "${HOME}/.vscode/extensions/budicuy.live-wallpaper-99.0.0" /var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0 2>/dev/null || true
    cp -rf "${SCRIPT_DIR}/vscode-extension"/* "${HOME}/.vscode/extensions/budicuy.live-wallpaper-99.0.0/" 2>/dev/null || true
    cp -rf "${SCRIPT_DIR}/vscode-extension"/* "/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0/" 2>/dev/null || true
    if [ -f "${SCRIPT_DIR}/scripts/register_extension.py" ]; then
        python3 "${SCRIPT_DIR}/scripts/register_extension.py" 2>/dev/null || true
    fi
fi

# Déploiement et activation automatique de l'extension GNOME Shell Hanabi si manquante sur cette machine
HANABI_UUID="hanabi-extension@jeffshee.github.io"
HANABI_SRC="${SCRIPT_DIR}/gnome-extension/${HANABI_UUID}"
HANABI_DEST="${HOME}/.local/share/gnome-shell/extensions/${HANABI_UUID}"
if [ -d "${HANABI_SRC}" ]; then
    mkdir -p "${HOME}/.local/share/gnome-shell/extensions/${HANABI_UUID}"
    cp -rf "${HANABI_SRC}"/* "${HANABI_DEST}/" 2>/dev/null || true
    mkdir -p "${HOME}/.local/share/glib-2.0/schemas"
    cp "${HANABI_SRC}/schemas/"*.xml "${HOME}/.local/share/glib-2.0/schemas/" 2>/dev/null || true
    command -v glib-compile-schemas &>/dev/null && glib-compile-schemas "${HOME}/.local/share/glib-2.0/schemas" 2>/dev/null || true
    if command -v gnome-extensions &>/dev/null; then
        gnome-extensions enable "${HANABI_UUID}" 2>/dev/null || true
    fi
fi

# Définition des dossiers d'environnement
XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
LOG_DIR="${HOME}/.cache/wallpapermaison/logs"
mkdir -p "${LOG_DIR}"

# Détection de l'exécutable Python (virtuel ou système)
if [ -x "${VENV_PYTHON}" ]; then
    PYTHON_EXEC="${VENV_PYTHON}"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
else
    echo "Erreur critique : Python 3 est introuvable." >&2
    exit 1
fi

# Export des variables d'environnement nécessaires
export LD_LIBRARY_PATH="${HOME}/.local/lib:${HOME}/reseau/Perso/.local/lib:${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io/lib:${LD_LIBRARY_PATH:-}"
export XDG_DATA_DIRS="${HOME}/.local/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export PATH="${HOME}/.local/bin:${SCRIPT_DIR}/scripts:${PATH}"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"
export PYSTRAY_BACKEND="${PYSTRAY_BACKEND:-xorg}"

if command -v systemctl &>/dev/null; then
    systemctl --user set-environment LD_LIBRARY_PATH="${LD_LIBRARY_PATH}" 2>/dev/null || true
fi

# Attente active de la session graphique si lancé au démarrage ou en mode démon
IS_DAEMON=false
IS_RESTORE=false
for arg in "$@"; do
    if [ "$arg" = "--daemon" ]; then IS_DAEMON=true; fi
    if [ "$arg" = "--restore" ]; then IS_RESTORE=true; fi
done

if [ "$IS_DAEMON" = true ] || [ "$IS_RESTORE" = true ]; then
    # Attente maximale de 10 secondes pour que la session Wayland ou X11 soit prête
    WAIT_COUNT=0
    while [ -z "${WAYLAND_DISPLAY}" ] && [ -z "${DISPLAY}" ] && [ $WAIT_COUNT -lt 20 ]; do
        sleep 0.5
        WAIT_COUNT=$((WAIT_COUNT + 1))
        if [ -n "${WAYLAND_DISPLAY}" ] || [ -n "${DISPLAY}" ]; then
            break
        fi
        # Tenter d'importer l'environnement depuis systemd --user si disponible
        if command -v systemctl &>/dev/null; then
            W_DISP=$(systemctl --user show-environment 2>/dev/null | grep "^WAYLAND_DISPLAY=" | cut -d= -f2- || true)
            X_DISP=$(systemctl --user show-environment 2>/dev/null | grep "^DISPLAY=" | cut -d= -f2- || true)
            [ -n "$W_DISP" ] && export WAYLAND_DISPLAY="$W_DISP"
            [ -n "$X_DISP" ] && export DISPLAY="$X_DISP"
        fi
    done
fi

# Gestion de la redirection des logs en mode démon sans terminal
if [ "$IS_DAEMON" = true ] && [ ! -t 1 ]; then
    exec >> "${LOG_DIR}/autostart_daemon.log" 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Démarrage WallpaperMaison Daemon (PID $$)..."
fi

exec "${PYTHON_EXEC}" "${SCRIPT_DIR}/app/main.py" "$@"
