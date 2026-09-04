#!/usr/bin/env bash
# ==============================================================================
# Script d'installation universel de WallpaperMaison pour Linux Fedora
# Compatible mode autonome (sans droits root), mode persistant NFS / réseau IUT,
# et exécutable en une ligne depuis GitHub via curl.
# ==============================================================================
set -e

APP_NAME="WallpaperMaison"
REPO_URL="https://github.com/Shunikai972/Wallpaper.git"

# ------------------------------------------------------------------------------
# 0. Gestion du mode One-Liner (ex: curl ... | bash)
# ------------------------------------------------------------------------------
if [ -z "${BASH_SOURCE[0]}" ] || [ "${BASH_SOURCE[0]}" = "bash" ] || [ "${BASH_SOURCE[0]}" = "/dev/stdin" ]; then
    echo "=========================================================="
    echo "  🚀 Installation en une ligne de ${APP_NAME}             "
    echo "=========================================================="

    # Choix du dossier cible : réseau persistant si présent, sinon dossier utilisateur local
    if [ -d "${HOME}/reseau/Perso/Bureau" ]; then
        TARGET_DIR="${HOME}/reseau/Perso/Bureau/Wallpaper"
    elif [ -d "${HOME}/reseau/Perso" ]; then
        TARGET_DIR="${HOME}/reseau/Perso/Wallpaper"
    else
        TARGET_DIR="${HOME}/Wallpaper"
    fi

    if [ -d "${TARGET_DIR}/.git" ]; then
        echo "✓ Dépôt existant détecté dans ${TARGET_DIR}."
        echo "  Mise à jour depuis GitHub..."
        git -C "${TARGET_DIR}" pull --quiet || true
    else
        echo "📥 Clonage du dépôt dans ${TARGET_DIR}..."
        mkdir -p "$(dirname "${TARGET_DIR}")"
        git clone "${REPO_URL}" "${TARGET_DIR}"
    fi

    echo "Lancement de l'installateur local..."
    exec bash "${TARGET_DIR}/scripts/install.sh" "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
DESKTOP_FILE_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
PERSISTENT_NFS="${HOME}/reseau/Perso"

echo "=========================================================="
echo "      Installation de ${APP_NAME} sur Linux Fedora        "
echo "=========================================================="
echo "Répertoire de l'application : ${SCRIPT_DIR}"
echo ""

# ------------------------------------------------------------------------------
# 1. Vérification de l'environnement Fedora
# ------------------------------------------------------------------------------
if [ -f /etc/fedora-release ]; then
    FEDORA_VER=$(cat /etc/fedora-release)
    echo "✓ Système détecté : ${FEDORA_VER}"
else
    echo "ℹ Note : Système Linux non-Fedora détecté, poursuite normale."
fi

# ------------------------------------------------------------------------------
# 2. Détection et choix du mode persistant (Réseau IUT / NFS)
# ------------------------------------------------------------------------------
IS_PERSISTENT=false
MARKER_FILE="${SCRIPT_DIR}/.persistent_mode"

# Analyse des paramètres en ligne de commande
for arg in "$@"; do
    case "$arg" in
        --persistent|-p) IS_PERSISTENT=true ;;
        --local|-l) IS_PERSISTENT=false ;;
        -y|--yes) ASSUME_YES=true ;;
    esac
done

if [ -d "${PERSISTENT_NFS}" ] && [ "$IS_PERSISTENT" = false ] && [ "$1" != "--local" ]; then
    echo ""
    echo "📁 Stockage réseau persistant détecté : ${PERSISTENT_NFS}"
    echo "   (Ce dossier conserve vos fichiers sur tous les ordinateurs du réseau IUT)"
    echo ""

    PROMPT_ANSWER=""
    if [ "$ASSUME_YES" = true ]; then
        PROMPT_ANSWER="o"
    elif [ -e /dev/tty ]; then
        read -p "Souhaitez-vous une installation PERSISTANTE (sauvegarde automatique de vos fonds, playlists et réglages sur le réseau) ? [O/n] : " -r PROMPT_ANSWER < /dev/tty || true
    fi

    if [[ "$PROMPT_ANSWER" =~ ^[nN]$ ]]; then
        IS_PERSISTENT=false
        rm -f "${MARKER_FILE}"
        echo "ℹ Mode local choisi."
    else
        IS_PERSISTENT=true
        touch "${MARKER_FILE}"
        echo "✓ Mode persistant réseau activé."
    fi
fi

# ------------------------------------------------------------------------------
# 3. Vérification des outils système & multimédia
# ------------------------------------------------------------------------------
echo ""
echo "--- [1/5] Analyse des dépendances et lecteurs multimédias ---"

if command -v python3 &>/dev/null; then
    echo "✓ Python 3 disponible : $(python3 --version)"
fi

if command -v ffmpeg &>/dev/null; then
    echo "✓ FFmpeg disponible : $(command -v ffmpeg)"
fi

if command -v mpv &>/dev/null; then
    echo "✓ MPV disponible : $(command -v mpv)"
elif [ -x "${HOME}/.local/bin/mpv" ]; then
    echo "✓ Wrapper MPV disponible : ${HOME}/.local/bin/mpv"
elif command -v flatpak &>/dev/null && flatpak info io.mpv.Mpv &>/dev/null; then
    echo "✓ MPV officiel Flatpak disponible (io.mpv.Mpv / tous codecs H264 & HEVC activés)"
    mkdir -p "${HOME}/.local/bin"
    cat << 'EOF_MPV' > "${HOME}/.local/bin/mpv"
#!/bin/bash
exec flatpak run --filesystem=host io.mpv.Mpv "$@"
EOF_MPV
    chmod +x "${HOME}/.local/bin/mpv"
elif command -v flatpak &>/dev/null; then
    echo "ℹ Installation de MPV officiel via Flatpak (io.mpv.Mpv)..."
    flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
    flatpak install --user -y flathub io.mpv.Mpv 2>/dev/null || true
    if flatpak info io.mpv.Mpv &>/dev/null; then
        mkdir -p "${HOME}/.local/bin"
        cat << 'EOF_MPV' > "${HOME}/.local/bin/mpv"
#!/bin/bash
exec flatpak run --filesystem=host io.mpv.Mpv "$@"
EOF_MPV
        chmod +x "${HOME}/.local/bin/mpv"
        echo "✓ MPV configuré dans ${HOME}/.local/bin/mpv"
    fi
else
    echo "ℹ MPV non installé : le moteur autonome haute fidélité prendra le relais pour les vidéos"
fi

if ! rpm -q webkit2gtk4.1 &>/dev/null && ! rpm -q webkit2gtk4.0 &>/dev/null; then
    echo "ℹ WebKit2GTK : utilisation des bibliothèques système Fedora"
else
    echo "✓ WebKit2GTK disponible pour l'interface PyWebView"
fi

# ------------------------------------------------------------------------------
# 4. Préparation de l'environnement virtuel Python autonome
# ------------------------------------------------------------------------------
echo ""
echo "--- [2/5] Préparation de l'environnement Python autonome ---"
if [ ! -d "${VENV_DIR}" ]; then
    echo "Création du virtualenv avec accès aux paquets système dans ${VENV_DIR}..."
    python3 -m venv --system-site-packages "${VENV_DIR}"
else
    echo "Environnement virtuel existant détecté."
    if [ -f "${VENV_DIR}/pyvenv.cfg" ]; then
        sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' "${VENV_DIR}/pyvenv.cfg" 2>/dev/null || true
    fi
fi

echo "Installation / Vérification des dépendances Python..."
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" --quiet
echo "✓ Dépendances Python prêtes."

# ------------------------------------------------------------------------------
# 5. Configuration des dossiers locaux / persistants
# ------------------------------------------------------------------------------
echo ""
echo "--- [3/5] Configuration des dossiers et bibliothèque ---"

mkdir -p "${DESKTOP_FILE_DIR}"
mkdir -p "${ICON_DIR}"
mkdir -p "${HOME}/.local/bin"

if [ "$IS_PERSISTENT" = true ]; then
    P_CONFIG="${PERSISTENT_NFS}/.config/wallpapermaison"
    P_DATA="${PERSISTENT_NFS}/.local/share/wallpapermaison"
    P_CACHE="${PERSISTENT_NFS}/.cache/wallpapermaison"
    P_WALLPAPERS="${PERSISTENT_NFS}/Images/Wallpapers"

    mkdir -p "${P_CONFIG}"
    mkdir -p "${P_DATA}"
    mkdir -p "${P_CACHE}/thumbnails"
    mkdir -p "${P_CACHE}/processed"
    mkdir -p "${P_CACHE}/logs"
    mkdir -p "${P_WALLPAPERS}"

    # Liens symboliques locaux pour transparence applicative
    mkdir -p "${HOME}/.config" "${HOME}/.cache" "${HOME}/.local/share"
    ln -sfn "${P_CONFIG}" "${HOME}/.config/wallpapermaison"
    ln -sfn "${P_DATA}" "${HOME}/.local/share/wallpapermaison"
    ln -sfn "${P_CACHE}" "${HOME}/.cache/wallpapermaison"
    mkdir -p "${HOME}/Pictures"
    ln -sfn "${P_WALLPAPERS}" "${HOME}/Pictures/Wallpapers" 2>/dev/null || true

    WALLPAPER_DIR="${P_WALLPAPERS}"
    echo "✓ Espace persistant configuré dans ${PERSISTENT_NFS}"
else
    WALLPAPER_DIR="${HOME}/Pictures/Wallpapers"
    mkdir -p "${HOME}/.config/wallpapermaison"
    mkdir -p "${HOME}/.cache/wallpapermaison/thumbnails"
    mkdir -p "${HOME}/.cache/wallpapermaison/processed"
    mkdir -p "${HOME}/.cache/wallpapermaison/logs"
    mkdir -p "${WALLPAPER_DIR}"
fi

# Copie de l'icône de l'application
if [ -f "${SCRIPT_DIR}/ui/assets/logo.svg" ]; then
    cp "${SCRIPT_DIR}/ui/assets/logo.svg" "${ICON_DIR}/wallpapermaison.svg"
    echo "✓ Icône installée dans ${ICON_DIR}/wallpapermaison.svg"
fi

# Copie d'exemples de fonds d'écran système si le dossier est vide
WALLPAPER_COUNT=$(find "${WALLPAPER_DIR}" -maxdepth 1 -type f 2>/dev/null | wc -l)
if [ "$WALLPAPER_COUNT" -eq 0 ]; then
    echo "Initialisation de la bibliothèque avec les fonds d'écran de démarrage..."
    if [ -d "/usr/share/backgrounds/fedora-workstation" ]; then
        cp /usr/share/backgrounds/fedora-workstation/*.webp "${WALLPAPER_DIR}/" 2>/dev/null || true
    fi
    if [ -d "/usr/share/backgrounds/gnome" ]; then
        cp /usr/share/backgrounds/gnome/*.svg "${WALLPAPER_DIR}/" 2>/dev/null || true
        cp /usr/share/backgrounds/gnome/*.png "${WALLPAPER_DIR}/" 2>/dev/null || true
    fi
    echo "✓ Fonds d'écran d'exemple ajoutés dans ${WALLPAPER_DIR}"
fi

# ------------------------------------------------------------------------------
# 6. Indexation automatique des dossiers de fonds d'écran
# ------------------------------------------------------------------------------
echo ""
echo "--- [4/5] Indexation de vos fonds d'écran ---"
SCAN_DIRS=("${WALLPAPER_DIR}")
if [ -d "${HOME}/reseau/Perso/Téléchargements/test" ]; then
    SCAN_DIRS+=("${HOME}/reseau/Perso/Téléchargements/test")
fi

for sdir in "${SCAN_DIRS[@]}"; do
    echo "Indexation de : ${sdir}..."
    "${VENV_DIR}/bin/python" "${SCRIPT_DIR}/app/main.py" --scan "${sdir}" >/dev/null 2>&1 || true
done
echo "✓ Indexation terminée."

# ------------------------------------------------------------------------------
# 7. Création du raccourci Bureau et script de reconnexion automatique
# ------------------------------------------------------------------------------
echo ""
echo "--- [5/5] Intégration au système GNOME ---"
DESKTOP_FILE="${DESKTOP_FILE_DIR}/wallpapermaison.desktop"

cat <<EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Type=Application
Name=WallpaperMaison
GenericName=Gestionnaire de Fonds d'Écran
Comment=Alternative moderne à Wallpaper Engine pour Linux Fedora
Exec=${SCRIPT_DIR}/scripts/run.sh %F
Icon=wallpapermaison
Terminal=false
Categories=Utility;Settings;DesktopSettings;
Keywords=wallpaper;background;engine;wayland;video;gnome;
StartupNotify=true
X-GNOME-UsesNotifications=true
EOF

chmod +x "${DESKTOP_FILE}"
chmod +x "${SCRIPT_DIR}/scripts/run.sh"
chmod +x "${SCRIPT_DIR}/scripts/install.sh"
chmod +x "${SCRIPT_DIR}/app/wallpaper/engines/video_bg_worker.py" 2>/dev/null || true

# 8. Configuration du démarrage automatique au login (GNOME Autostart & systemd user)
AUTOSTART_DIR="${HOME}/.config/autostart"
mkdir -p "${AUTOSTART_DIR}"
AUTOSTART_DESKTOP="${AUTOSTART_DIR}/wallpapermaison.desktop"

cat <<EOF > "${AUTOSTART_DESKTOP}"
[Desktop Entry]
Type=Application
Name=WallpaperMaison Daemon
Comment=Démarrage automatique et restauration de vos fonds d'écran
Exec=${SCRIPT_DIR}/scripts/run.sh --daemon
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
EOF

if [ "$IS_PERSISTENT" = true ]; then
    mkdir -p "${PERSISTENT_NFS}/.config/autostart"
    cp "${AUTOSTART_DESKTOP}" "${PERSISTENT_NFS}/.config/autostart/wallpapermaison.desktop"
fi

# Configuration du service systemd utilisateur
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
mkdir -p "${SYSTEMD_USER_DIR}/graphical-session.target.wants"
cat <<EOF > "${SYSTEMD_USER_DIR}/wallpapermaison.service"
[Unit]
Description=WallpaperMaison Service de Fond d'Écran
After=graphical-session.target gnome-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=${SCRIPT_DIR}/scripts/run.sh --daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
EOF

ln -sf "${SYSTEMD_USER_DIR}/wallpapermaison.service" "${SYSTEMD_USER_DIR}/graphical-session.target.wants/wallpapermaison.service" 2>/dev/null || true
if [ "$IS_PERSISTENT" = true ]; then
    mkdir -p "${PERSISTENT_NFS}/.config/systemd/user/graphical-session.target.wants"
    cp "${SYSTEMD_USER_DIR}/wallpapermaison.service" "${PERSISTENT_NFS}/.config/systemd/user/"
    cp -P "${SYSTEMD_USER_DIR}/graphical-session.target.wants/wallpapermaison.service" "${PERSISTENT_NFS}/.config/systemd/user/graphical-session.target.wants/" 2>/dev/null || true
fi
systemctl --user daemon-reload 2>/dev/null || true

# 9. Création d'un script d'auto-restauration dans ~/.bashrc.d pour nouveau PC
AUTOSTART_RC_DIR="${HOME}/.bashrc.d"
mkdir -p "${AUTOSTART_RC_DIR}"
cat <<EOF > "${AUTOSTART_RC_DIR}/wallpapermaison.sh"
# WallpaperMaison - Restauration automatique sur nouveau poste IUT
WP_DIR="${SCRIPT_DIR}"

if [ -d "\$WP_DIR" ]; then
    export PATH="\${WP_DIR}/scripts:\${HOME}/.local/bin:\$PATH"
    alias wallpapermaison="\${WP_DIR}/scripts/run.sh"

    if [ ! -f "\${HOME}/.config/autostart/wallpapermaison.desktop" ]; then
        mkdir -p "\${HOME}/.config/autostart" 2>/dev/null
        cp "\${WP_DIR}/scripts/autostart.desktop" "\${HOME}/.config/autostart/wallpapermaison.desktop" 2>/dev/null || true
    fi
fi
EOF

if [ "$IS_PERSISTENT" = true ] && [ -d "${PERSISTENT_NFS}/.bashrc.d" ]; then
    cp "${AUTOSTART_RC_DIR}/wallpapermaison.sh" "${PERSISTENT_NFS}/.bashrc.d/wallpapermaison.sh" 2>/dev/null || true
fi

# Mise à jour du .bashrc local si nécessaire
if [ -f "${HOME}/.bashrc" ] && ! grep -q "bashrc.d" "${HOME}/.bashrc"; then
    cat << 'EOF' >> "${HOME}/.bashrc"

if [ -d ~/.bashrc.d ]; then
  for rc in ~/.bashrc.d/*; do
    [ -f "$rc" ] && . "$rc"
  done
fi
EOF
fi

echo "✓ Raccourci d'application créé : ${DESKTOP_FILE}"
echo ""
echo "=========================================================="
if [ "$IS_PERSISTENT" = true ]; then
    echo "🎉 Installation PERSISTANTE terminée avec succès !"
    echo "Vos fonds et réglages sont stockés sur le réseau et conservés"
    echo "sur n'importe quel ordinateur de l'IUT."
else
    echo "🎉 Installation locale terminée avec succès !"
fi
echo ""
echo "Pour lancer WallpaperMaison :"
echo "  1. Menu d'applications GNOME -> 'WallpaperMaison'"
echo "  2. Ou en terminal : ${SCRIPT_DIR}/scripts/run.sh"
echo ""
echo "💡 Commande en une ligne à copier depuis GitHub sur un nouveau poste :"
echo "bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Shunikai972/Wallpaper/main/scripts/install.sh)\""
echo "=========================================================="
