#!/usr/bin/env bash
# ==============================================================================
# WallpaperMaison - Script d'installation & configuration idempotent
# Compatible : Fedora Silverblue / Workstation, Ubuntu, Debian, Arch
# Supporte : Mode autonome sans root, réseau persistant NFS / IUT
# ==============================================================================
set -euo pipefail

APP_NAME="WallpaperMaison"

# ------------------------------------------------------------------------------
# 1. Détection dynamique du répertoire du projet
# ------------------------------------------------------------------------------
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/scripts/run.sh" ]; then
    for candidate in \
        "${HOME}/Wallpaper" \
        "${HOME}/Bureau/Wallpaper" \
        "${HOME}/Desktop/Wallpaper" \
        "${HOME}/reseau/Perso/Bureau/Wallpaper" \
        "/var/home/${USER}/Wallpaper" \
        "/home/${USER}/Wallpaper" \
        "/var/home/${USER}/reseau/Perso/Bureau/Wallpaper"; do
        if [ -f "$candidate/scripts/run.sh" ]; then
            SCRIPT_DIR="$candidate"
            break
        fi
    done
fi

if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/scripts/run.sh" ]; then
    echo "❌ Erreur : Impossible de localiser le répertoire racine de WallpaperMaison." >&2
    exit 1
fi

echo "===================================================================="
echo "  🚀 Configuration & Restauration de ${APP_NAME}"
echo "===================================================================="
echo "📁 Répertoire du projet : ${SCRIPT_DIR}"
echo "👤 Utilisateur           : ${USER} (UID: $(id -u))"
echo "🏠 Répertoire personnel  : ${HOME}"

# ------------------------------------------------------------------------------
# 2. Détection du système et de l'environnement graphique
# ------------------------------------------------------------------------------
OS_NAME="Linux"
if [ -f /etc/os-release ]; then
    OS_NAME=$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')
fi
echo "🐧 Système d'exploitation : ${OS_NAME}"
echo "🖥️  Session graphique      : ${XDG_SESSION_TYPE:-Inconnue (DISPLAY=${DISPLAY:-non}, WAYLAND=${WAYLAND_DISPLAY:-non})}"

PERSISTENT_NFS="${HOME}/reseau/Perso"
IS_PERSISTENT=false
if [ -d "${PERSISTENT_NFS}" ]; then
    IS_PERSISTENT=true
    echo "💾 Stockage persistant NFS détecté : ${PERSISTENT_NFS}"
else
    echo "ℹ️  Aucun stockage réseau NFS détecté (mode local standard)"
fi

# ------------------------------------------------------------------------------
# 3. Préparation des répertoires de base et de PATH
# ------------------------------------------------------------------------------
mkdir -p "${HOME}/.local/bin"
mkdir -p "${HOME}/.local/share/applications"
mkdir -p "${HOME}/.local/share/icons/hicolor/scalable/apps"
mkdir -p "${HOME}/.config/autostart"

export PATH="${HOME}/.local/bin:${SCRIPT_DIR}/scripts:${PATH}"
install -m 755 "${SCRIPT_DIR}/scripts/session-start.sh" "${HOME}/.local/bin/wallpapermaison-session-start"
SESSION_LAUNCHER="${HOME}/.local/bin/wallpapermaison-session-start"
if [ "$IS_PERSISTENT" = true ]; then
    mkdir -p "${PERSISTENT_NFS}/.local/bin"
    install -m 755 "${SCRIPT_DIR}/scripts/session-start.sh" "${PERSISTENT_NFS}/.local/bin/wallpapermaison-session-start"
    SESSION_LAUNCHER="${PERSISTENT_NFS}/.local/bin/wallpapermaison-session-start"
fi

# ------------------------------------------------------------------------------
# 4. Dépendances multimédia & Wrappers Flatpak (MPV & FFmpeg avec codecs complets)
# ------------------------------------------------------------------------------
echo ""
echo "--- [1/6] Vérification des codecs et lecteurs vidéo ---"

NEED_MPV_WRAPPER=false

if command -v mpv &>/dev/null; then
    echo "✓ Binaire mpv trouvé dans le PATH : $(command -v mpv)"
elif [ -x "${HOME}/.local/bin/mpv" ]; then
    echo "✓ Wrapper mpv existant dans ${HOME}/.local/bin/mpv"
else
    NEED_MPV_WRAPPER=true
fi

# Vérification du codec H.264 dans ffmpeg hôte
SYSTEM_FFMPEG_HAS_H264=true
if command -v ffmpeg &>/dev/null; then
    if ! ffmpeg -codecs 2>/dev/null | grep -q "E.*h264"; then
        SYSTEM_FFMPEG_HAS_H264=false
    fi
else
    SYSTEM_FFMPEG_HAS_H264=false
fi

# Configuration Flatpak pour mpv et ffmpeg complet si nécessaire
if [ "$NEED_MPV_WRAPPER" = true ] || [ "$SYSTEM_FFMPEG_HAS_H264" = false ]; then
    if command -v flatpak &>/dev/null; then
        FLATPAK_APP=""
        if flatpak info io.mpv.Mpv &>/dev/null; then
            FLATPAK_APP="io.mpv.Mpv"
        elif flatpak info io.github.celluloid_player.Celluloid &>/dev/null; then
            FLATPAK_APP="io.github.celluloid_player.Celluloid"
        else
            echo "📥 Installation du Flatpak officiel io.mpv.Mpv (avec codecs H.264 / HEVC)..."
            flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
            flatpak install --user -y flathub io.mpv.Mpv 2>/dev/null || true
            if flatpak info io.mpv.Mpv &>/dev/null; then
                FLATPAK_APP="io.mpv.Mpv"
            fi
        fi

        if [ -n "$FLATPAK_APP" ]; then
            echo "✓ Flatpak ${FLATPAK_APP} opérationnel pour mpv et ffmpeg."
            # Wrapper MPV
            cat << 'EOF_MPV' > "${HOME}/.local/bin/mpv"
#!/usr/bin/env bash
if flatpak info io.mpv.Mpv &>/dev/null; then
    exec flatpak run --filesystem=host io.mpv.Mpv "$@"
elif flatpak info io.github.celluloid_player.Celluloid &>/dev/null; then
    exec flatpak run --filesystem=host --command=mpv io.github.celluloid_player.Celluloid "$@"
fi
exec mpv "$@"
EOF_MPV
            chmod +x "${HOME}/.local/bin/mpv"
            echo "✓ Wrapper ${HOME}/.local/bin/mpv configuré."

            # Wrapper FFmpeg complet
            cat << 'EOF_FFMPEG' > "${HOME}/.local/bin/ffmpeg-full"
#!/usr/bin/env bash
if flatpak info io.mpv.Mpv &>/dev/null; then
    exec flatpak run --filesystem=host --command=ffmpeg io.mpv.Mpv "$@"
elif flatpak info io.github.celluloid_player.Celluloid &>/dev/null; then
    exec flatpak run --filesystem=host --command=ffmpeg io.github.celluloid_player.Celluloid "$@"
fi
exec ffmpeg "$@"
EOF_FFMPEG
            chmod +x "${HOME}/.local/bin/ffmpeg-full"
            echo "✓ Wrapper ${HOME}/.local/bin/ffmpeg-full configuré."
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 5. Environnement virtuel Python et dépendances
# ------------------------------------------------------------------------------
echo ""
echo "--- [2/6] Préparation de l'environnement virtuel Python ---"
VENV_DIR="${SCRIPT_DIR}/.venv"

if [ ! -d "${VENV_DIR}" ]; then
    echo "Création de l'environnement virtuel Python dans ${VENV_DIR}..."
    python3 -m venv --system-site-packages "${VENV_DIR}"
else
    echo "✓ Environnement virtuel existant dans ${VENV_DIR}."
    if [ -f "${VENV_DIR}/pyvenv.cfg" ]; then
        sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' "${VENV_DIR}/pyvenv.cfg" 2>/dev/null || true
    fi
fi

if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
    echo "Vérification des dépendances pip..."
    if ! "${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" --quiet; then
        echo "❌ Installation des dépendances Python impossible. Vérifiez pip et la connexion réseau." >&2
        exit 1
    fi
    echo "✓ Dépendances Python installées."
fi

# ------------------------------------------------------------------------------
# 6. Configuration des répertoires persistants et liens symboliques
# ------------------------------------------------------------------------------
echo ""
echo "--- [3/6] Configuration du stockage persistant ---"

if [ "$IS_PERSISTENT" = true ]; then
    P_CONFIG="${PERSISTENT_NFS}/.config/wallpapermaison"
    P_DATA="${PERSISTENT_NFS}/.local/share/wallpapermaison"
    P_CACHE="${PERSISTENT_NFS}/.cache/wallpapermaison"
    P_WALLPAPERS="${PERSISTENT_NFS}/Images/Wallpapers"

    mkdir -p "${P_CONFIG}" "${P_DATA}" "${P_WALLPAPERS}"
    mkdir -p "${P_CACHE}/thumbnails" "${P_CACHE}/processed" "${P_CACHE}/logs"

    # Liens symboliques locaux
    mkdir -p "${HOME}/.config" "${HOME}/.cache" "${HOME}/.local/share"
    if [ ! -L "${HOME}/.config/wallpapermaison" ] || [ "$(realpath "${HOME}/.config/wallpapermaison" 2>/dev/null)" != "$(realpath "${P_CONFIG}")" ]; then
        ln -sfn "${P_CONFIG}" "${HOME}/.config/wallpapermaison"
    fi
    if [ ! -L "${HOME}/.local/share/wallpapermaison" ] || [ "$(realpath "${HOME}/.local/share/wallpapermaison" 2>/dev/null)" != "$(realpath "${P_DATA}")" ]; then
        ln -sfn "${P_DATA}" "${HOME}/.local/share/wallpapermaison"
    fi
    if [ ! -L "${HOME}/.cache/wallpapermaison" ] || [ "$(realpath "${HOME}/.cache/wallpapermaison" 2>/dev/null)" != "$(realpath "${P_CACHE}")" ]; then
        ln -sfn "${P_CACHE}" "${HOME}/.cache/wallpapermaison"
    fi
    mkdir -p "${HOME}/Pictures"
    if [ ! -L "${HOME}/Pictures/Wallpapers" ] || [ "$(realpath "${HOME}/Pictures/Wallpapers" 2>/dev/null)" != "$(realpath "${P_WALLPAPERS}")" ]; then
        ln -sfn "${P_WALLPAPERS}" "${HOME}/Pictures/Wallpapers" 2>/dev/null || true
    fi

    # Activer start_at_login dans la configuration persistante si présente
    if [ -f "${P_CONFIG}/config.json" ]; then
        sed -i 's/"start_at_login": false/"start_at_login": true/' "${P_CONFIG}/config.json" 2>/dev/null || true
    fi
    echo "✓ Liens persistants configurés vers ${PERSISTENT_NFS}."
else
    mkdir -p "${HOME}/.config/wallpapermaison"
    mkdir -p "${HOME}/.local/share/wallpapermaison"
    mkdir -p "${HOME}/.cache/wallpapermaison/thumbnails"
    mkdir -p "${HOME}/.cache/wallpapermaison/processed"
    mkdir -p "${HOME}/.cache/wallpapermaison/logs"
    mkdir -p "${HOME}/Pictures/Wallpapers"
fi

# Installer l'icône de l'application
if [ -f "${SCRIPT_DIR}/ui/assets/logo.svg" ]; then
    cp "${SCRIPT_DIR}/ui/assets/logo.svg" "${HOME}/.local/share/icons/hicolor/scalable/apps/wallpapermaison.svg"
fi

# Rendre exécutables tous les scripts
chmod +x "${SCRIPT_DIR}/scripts/"*.sh 2>/dev/null || true
chmod +x "${SCRIPT_DIR}/app/wallpaper/engines/video_bg_worker.py" 2>/dev/null || true

# ------------------------------------------------------------------------------
# 7. Configuration de l'Autostart GNOME et du service Systemd Utilisateur
# ------------------------------------------------------------------------------
echo ""
echo "--- [4/6] Intégration GNOME Autostart & Systemd User ---"

# 7.1 Raccourci d'application GNOME (.desktop)
cat << EOF_DESK > "${HOME}/.local/share/applications/wallpapermaison.desktop"
[Desktop Entry]
Type=Application
Name=WallpaperMaison
GenericName=Gestionnaire de Fonds d'Écran
Comment=Alternative moderne à Wallpaper Engine pour Linux
Exec="${SCRIPT_DIR}/scripts/run.sh" %F
Icon=wallpapermaison
Terminal=false
Categories=Utility;Settings;DesktopSettings;
Keywords=wallpaper;background;engine;wayland;video;gnome;
StartupNotify=true
X-GNOME-UsesNotifications=true
EOF_DESK

# 7.2 GNOME Autostart (.desktop)
AUTOSTART_FILE="${HOME}/.config/autostart/wallpapermaison.desktop"
cat << EOF_AUTO > "${AUTOSTART_FILE}"
[Desktop Entry]
Type=Application
Name=WallpaperMaison Daemon
Comment=Démarrage automatique et restauration de vos fonds d'écran
Exec="${SESSION_LAUNCHER}" --daemon
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
EOF_AUTO

# 7.3 Retrait de l'ancien service global à l'utilisateur. XDG Autostart démarre
# le lanceur dans chaque session graphique, avec ses propres variables d'écran.
SYSTEMD_FILE="${HOME}/.config/systemd/user/wallpapermaison.service"
SYSTEMD_WANTS="${HOME}/.config/systemd/user/graphical-session.target.wants/wallpapermaison.service"
systemctl --user disable --now wallpapermaison.service 2>/dev/null || true
rm -f "${SYSTEMD_WANTS}" "${SYSTEMD_FILE}"
if [ "$IS_PERSISTENT" = true ]; then
    rm -f "${PERSISTENT_NFS}/.config/systemd/user/graphical-session.target.wants/wallpapermaison.service"
    rm -f "${PERSISTENT_NFS}/.config/systemd/user/wallpapermaison.service"
fi
systemctl --user daemon-reload 2>/dev/null || true

# Copie miroir sur le NFS persistant si différent
if [ "$IS_PERSISTENT" = true ]; then
    mkdir -p "${PERSISTENT_NFS}/.config/autostart"
    if [ "$(realpath "${HOME}/.config/autostart")" != "$(realpath "${PERSISTENT_NFS}/.config/autostart")" ]; then
        cp "${AUTOSTART_FILE}" "${PERSISTENT_NFS}/.config/autostart/wallpapermaison.desktop"
    fi

fi
echo "✓ Démarrage automatique configuré pour chaque session graphique (XDG Autostart)."

# Retire l'ancien alias qui empêchait code de démarrer après changement de machine.
for old_shell in "${HOME}/.bashrc.d/wallpapermaison.sh" "${PERSISTENT_NFS}/.bashrc.d/wallpapermaison.sh"; do
    if [ -f "$old_shell" ]; then sed -i '/alias code=/d' "$old_shell"; fi
done
mkdir -p "${HOME}/.config/wallpapermaison"
printf '%s\n' "$SCRIPT_DIR" > "${HOME}/.config/wallpapermaison/project-path"
if [ "$IS_PERSISTENT" = true ]; then
    mkdir -p "${PERSISTENT_NFS}/.config/wallpapermaison"
    printf '%s\n' "$SCRIPT_DIR" > "${PERSISTENT_NFS}/.config/wallpapermaison/project-path"
fi

# ------------------------------------------------------------------------------
# 9. Déploiement de l'Extension VS Code
# ------------------------------------------------------------------------------
echo ""
echo "--- [6/6] Déploiement de l'extension VS Code ---"
EXT_SRC="${SCRIPT_DIR}/vscode-extension"

if [ -d "$EXT_SRC" ]; then
    TARGET_VSCODE_EXT="${HOME}/.vscode/extensions/budicuy.live-wallpaper-99.0.0"
    mkdir -p "$TARGET_VSCODE_EXT"
    cp -r "$EXT_SRC"/. "$TARGET_VSCODE_EXT/"
    # Déploiement de root-shell
    if [ -f "${SCRIPT_DIR}/scripts/root-shell" ]; then
        mkdir -p "${HOME}/.local/bin"
        cp -f "${SCRIPT_DIR}/scripts/root-shell" "${HOME}/.local/bin/root-shell"
        chmod +x "${HOME}/.local/bin/root-shell"
        if [ "$IS_PERSISTENT" = true ]; then
            mkdir -p "${PERSISTENT_NFS}/.local/bin"
            if [ "$(realpath -m "${HOME}/.local/bin/root-shell")" != "$(realpath -m "${PERSISTENT_NFS}/.local/bin/root-shell")" ]; then
                cp -f "${SCRIPT_DIR}/scripts/root-shell" "${PERSISTENT_NFS}/.local/bin/root-shell" 2>/dev/null || true
            fi
            chmod +x "${PERSISTENT_NFS}/.local/bin/root-shell" 2>/dev/null || true
        fi
        echo "✓ Script root-shell déployé dans ~/.local/bin/root-shell"
    fi

    # Enregistrement dans extensions.json
    if [ -f "${SCRIPT_DIR}/scripts/register_extension.py" ]; then
        python3 "${SCRIPT_DIR}/scripts/register_extension.py" 2>/dev/null || true
    fi

    echo "✓ Extension VS Code déployée :"
    echo "  - ${TARGET_VSCODE_EXT}"
else
    echo "ℹ️  Dossier vscode-extension non trouvé dans ${SCRIPT_DIR}."
fi

# Déploiement du wrapper gjs pour injection transparente de LD_LIBRARY_PATH
mkdir -p "${HOME}/.local/bin"
cat << 'EOF_GJS' > "${HOME}/.local/bin/gjs"
#!/bin/bash
export LD_LIBRARY_PATH="${HOME}/.local/lib:${HOME}/reseau/Perso/.local/lib:${LD_LIBRARY_PATH:-}"
exec /usr/bin/gjs "$@"
EOF_GJS
chmod +x "${HOME}/.local/bin/gjs"
if [ "$IS_PERSISTENT" = true ]; then
    mkdir -p "${PERSISTENT_NFS}/.local/bin"
    if [ "$(realpath -m "${HOME}/.local/bin/gjs")" != "$(realpath -m "${PERSISTENT_NFS}/.local/bin/gjs")" ]; then
        cp -f "${HOME}/.local/bin/gjs" "${PERSISTENT_NFS}/.local/bin/gjs" 2>/dev/null || true
    fi
    chmod +x "${PERSISTENT_NFS}/.local/bin/gjs" 2>/dev/null || true
fi

# Déploiement des codecs vidéo Cisco OpenH264
mkdir -p "${HOME}/.local/lib"
H264_SRC=""
for cand in \
    "${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io/lib/libopenh264.so.8" \
    "${SCRIPT_DIR}/lib/libopenh264.so.8" \
    "${PERSISTENT_NFS}/.local/lib/libopenh264.so.8" \
    "${HOME}/.local/lib/libopenh264.so.8"; do
    if [ -f "$cand" ]; then
        H264_SRC="$cand"
        break
    fi
done
if [ -z "$H264_SRC" ]; then
    if command -v curl &>/dev/null && command -v bzip2 &>/dev/null; then
        curl -sL "http://ciscobinary.openh264.org/libopenh264-2.6.0-linux64.8.so.bz2" | bzip2 -d > "${HOME}/.local/lib/libopenh264.so.8" 2>/dev/null || true
        if [ -s "${HOME}/.local/lib/libopenh264.so.8" ]; then
            chmod 755 "${HOME}/.local/lib/libopenh264.so.8"
            H264_SRC="${HOME}/.local/lib/libopenh264.so.8"
        fi
    fi
fi
if [ -n "$H264_SRC" ] && [ -f "$H264_SRC" ]; then
    for target_dir in "${HOME}/.local/lib" "${PERSISTENT_NFS}/.local/lib" "${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io/lib"; do
        mkdir -p "$target_dir" 2>/dev/null || true
        [ ! -f "$target_dir/libopenh264.so.8" ] && cp -f "$H264_SRC" "$target_dir/libopenh264.so.8" 2>/dev/null || true
        ln -sf "libopenh264.so.8" "$target_dir/libopenh264.so.2.6.0" 2>/dev/null || true
        ln -sf "libopenh264.so.8" "$target_dir/libopenh264.so" 2>/dev/null || true
        chmod 755 "$target_dir"/libopenh264* 2>/dev/null || true
    done
    echo "✓ Codecs vidéo Cisco OpenH264 déployés dans ~/.local/lib"
fi

# ------------------------------------------------------------------------------
# 10. Déploiement de l'Extension GNOME Shell Hanabi (Vidéo native Mutter)
# ------------------------------------------------------------------------------
echo ""
echo "--- [7/7] Déploiement de l'extension GNOME Shell Hanabi ---"
HANABI_SRC="${SCRIPT_DIR}/gnome-extension/hanabi-extension@jeffshee.github.io"
HANABI_UUID="hanabi-extension@jeffshee.github.io"
HANABI_TARGET="${HOME}/.local/share/gnome-shell/extensions/${HANABI_UUID}"
SCHEMAS_TARGET="${HOME}/.local/share/glib-2.0/schemas"

# Nettoyer les anciens workers MPV externes en tâche de fond


if [ -d "$HANABI_SRC" ]; then
    mkdir -p "$(dirname "$HANABI_TARGET")"
    if [ "$(realpath -m "$HANABI_SRC")" != "$(realpath -m "$HANABI_TARGET")" ]; then
        mkdir -p "$HANABI_TARGET"
        cp -r "$HANABI_SRC"/* "$HANABI_TARGET/" 2>/dev/null || true
    fi

    # Installer et compiler le schéma GSettings local
    mkdir -p "$SCHEMAS_TARGET"
    if [ -f "${HANABI_SRC}/schemas/io.github.jeffshee.hanabi-extension.gschema.xml" ]; then
        cp "${HANABI_SRC}/schemas/io.github.jeffshee.hanabi-extension.gschema.xml" "$SCHEMAS_TARGET/" 2>/dev/null || true
        glib-compile-schemas "$SCHEMAS_TARGET" 2>/dev/null || true
    fi

    # Activer l'extension dans GSettings GNOME Shell
    if command -v gsettings &>/dev/null; then
        CURRENT_EXTS=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "[]")
        if ! echo "$CURRENT_EXTS" | grep -q "$HANABI_UUID"; then
            if [ "$CURRENT_EXTS" = "@as []" ] || [ "$CURRENT_EXTS" = "[]" ]; then
                gsettings set org.gnome.shell enabled-extensions "['$HANABI_UUID']" 2>/dev/null || true
            else
                NEW_EXTS=$(echo "$CURRENT_EXTS" | sed "s/]/, '$HANABI_UUID']/")
                gsettings set org.gnome.shell enabled-extensions "$NEW_EXTS" 2>/dev/null || true
            fi
        fi
    fi

    # Miroir sur le partage NFS persistant
    if [ "$IS_PERSISTENT" = true ]; then
        P_EXT="${PERSISTENT_NFS}/.local/share/gnome-shell/extensions/${HANABI_UUID}"
        if [ "$(realpath -m "$HANABI_SRC")" != "$(realpath -m "$P_EXT")" ]; then
            mkdir -p "$(dirname "$P_EXT")"
            mkdir -p "$P_EXT"
            cp -r "$HANABI_SRC"/* "$P_EXT/" 2>/dev/null || true
        fi
        mkdir -p "${PERSISTENT_NFS}/.local/share/glib-2.0/schemas"
        cp "${HANABI_SRC}/schemas/io.github.jeffshee.hanabi-extension.gschema.xml" "${PERSISTENT_NFS}/.local/share/glib-2.0/schemas/" 2>/dev/null || true
        glib-compile-schemas "${PERSISTENT_NFS}/.local/share/glib-2.0/schemas" 2>/dev/null || true
    fi

    echo "✓ Extension GNOME Shell Hanabi déployée (injection native Mutter) :"
    echo "  - ${HANABI_TARGET}"
else
    echo "ℹ️  Extension Hanabi non présente dans ${SCRIPT_DIR}/gnome-extension."
fi

# Détection du premier wallpaper vidéo pour l'initialisation de session et VS Code
FIRST_WALLPAPER=""
if [ -d "${SCRIPT_DIR}/Wallpaper" ]; then
    for v in "${SCRIPT_DIR}/Wallpaper"/*.mp4 "${SCRIPT_DIR}/Wallpaper"/*.webm; do
        if [ -f "$v" ]; then
            FIRST_WALLPAPER="$(readlink -f "$v")"
            break
        fi
    done
fi

if [ -n "$FIRST_WALLPAPER" ]; then
    # Configurer le fond d'écran initial dans Hanabi GSettings si non renseigné
    if command -v gsettings &>/dev/null; then
        CURRENT_VIDEO_SETTING=$(gsettings get io.github.jeffshee.hanabi-extension video-path 2>/dev/null || echo "''")
        CURRENT_VIDEO_CLEAN=$(echo "$CURRENT_VIDEO_SETTING" | tr -d "'\"")
        if [ -z "$CURRENT_VIDEO_CLEAN" ] || [ ! -f "$CURRENT_VIDEO_CLEAN" ]; then
            gsettings set io.github.jeffshee.hanabi-extension video-path "$FIRST_WALLPAPER" 2>/dev/null || true
            echo "✓ Fond d'écran initial configuré dans GNOME Hanabi : $(basename "$FIRST_WALLPAPER")"
        fi
    fi

    # Initialiser current_wallpaper.json
    mkdir -p "${HOME}/.config/wallpapermaison"
    if [ ! -f "${HOME}/.config/wallpapermaison/current_wallpaper.json" ]; then
        cat << EOF_INIT_JSON > "${HOME}/.config/wallpapermaison/current_wallpaper.json"
{
  "path": "${FIRST_WALLPAPER}",
  "media_type": "video",
  "source": "setup",
  "timestamp": $(date +%s)
}
EOF_INIT_JSON
    fi
    if [ "$IS_PERSISTENT" = true ]; then
        mkdir -p "${PERSISTENT_NFS}/.config/wallpapermaison"
        [ ! -f "${PERSISTENT_NFS}/.config/wallpapermaison/current_wallpaper.json" ] && cp "${HOME}/.config/wallpapermaison/current_wallpaper.json" "${PERSISTENT_NFS}/.config/wallpapermaison/current_wallpaper.json" 2>/dev/null || true
    fi

    # Initialiser .env si absent ou corriger ROTATION_FOLDER
    if [ ! -f "${SCRIPT_DIR}/.env" ] && [ -f "${SCRIPT_DIR}/.env.example" ]; then
        cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
    fi
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        CUR_RF=$(grep -E '^ROTATION_FOLDER=' "${SCRIPT_DIR}/.env" 2>/dev/null | cut -d= -f2- | tr -d '"'\'' ' || true)
        if [ -z "$CUR_RF" ] || [ ! -d "$CUR_RF" ]; then
            sed -i 's|^ROTATION_FOLDER=.*|ROTATION_FOLDER="Wallpaper"|' "${SCRIPT_DIR}/.env" 2>/dev/null || true
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 11. Intégration et injection native directe dans Visual Studio Code
# ------------------------------------------------------------------------------
echo ""
echo "[11/12] Configuration et injection native dans Visual Studio Code..."

# Installe un lanceur distinct et conserve la commande système `code`.
install -m 755 "${SCRIPT_DIR}/scripts/code-launcher.sh" "${HOME}/.local/bin/wallpapermaison-code"
# Réparer uniquement les lanceurs écrits par une ancienne version du projet.
if [ -f "${HOME}/.local/bin/code" ] && grep -q 'Visual Studio Code Portable Launcher avec Live Wallpaper' "${HOME}/.local/bin/code"; then
    rm -f "${HOME}/.local/bin/code"
fi
python3 "${SCRIPT_DIR}/scripts/write_desktop_entries.py" "$SCRIPT_DIR"
echo "✓ Lanceur WallpaperMaison pour VS Code installé."

# ------------------------------------------------------------------------------
# 12. Rapport de validation & Auto-Test
# ------------------------------------------------------------------------------
echo ""
echo "===================================================================="
echo "  🔍 Auto-Test de l'environnement"
echo "===================================================================="

TEST_OK=true

# Test Python
if "${VENV_DIR}/bin/python" -c "import gi, PIL, sqlite3; print('  ✓ Python + PyGObject + Pillow + SQLite : OK')" 2>/dev/null; then
    :
else
    echo "  ⚠️  Attention : Certaines bibliothèques Python n'ont pas pu être importées."
    TEST_OK=false
fi

# Test Colorimétrie Python
if PYTHONPATH="${SCRIPT_DIR}" "${VENV_DIR}/bin/python" -c "from app.image_processing.colorimetry import ColorPaletteExtractor; print('  ✓ Moteur de colorimétrie Python : OK')" 2>/dev/null; then
    :
else
    echo "  ⚠️  Erreur import moteur colorimétrie."
    TEST_OK=false
fi

# Test Moteur Vidéo Natif GNOME Shell (Hanabi)
if PYTHONPATH="${SCRIPT_DIR}" "${VENV_DIR}/bin/python" -c "from app.wallpaper.engines.hanabi_engine import HanabiWallpaperEngine; assert HanabiWallpaperEngine().is_available(); print('  ✓ Moteur vidéo GNOME Shell natif (Hanabi / Mutter) : ACTIF')" 2>/dev/null; then
    :
else
    echo "  ℹ️  Moteur Hanabi : Non actif sur cette session (relais automatique sur GTK/MPV)."
fi

echo "===================================================================="
if [ "$TEST_OK" = true ]; then
    echo "  🎉 Configuration terminée avec SUCCÈS !"
else
    echo "  ⚠️  Configuration terminée avec des avertissements (voir ci-dessus)."
fi
echo "===================================================================="
echo ""
echo "Pour démarrer WallpaperMaison maintenant :"
echo "  ${SCRIPT_DIR}/scripts/run.sh"
echo ""
echo "Pour vérifier le statut du service d'arrière-plan :"
echo "  cat ~/.cache/wallpapermaison/logs/session-start.log"
echo ""
