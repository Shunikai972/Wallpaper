#!/usr/bin/env bash
# ==============================================================================
# Script d'installation de WallpaperMaison pour Linux Fedora
# ==============================================================================
set -e

APP_NAME="WallpaperMaison"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
DESKTOP_FILE_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"

echo "=========================================================="
echo "      Installation de ${APP_NAME} sur Linux Fedora        "
echo "=========================================================="
echo "Répertoire de l'application : ${SCRIPT_DIR}"
echo ""

# 1. Vérification de l'environnement Fedora
if [ -f /etc/fedora-release ]; then
    FEDORA_VER=$(cat /etc/fedora-release)
    echo "✓ Système détecté : ${FEDORA_VER}"
else
    echo "ℹ Note : Ce système ne semble pas être Fedora, mais le script continuera."
fi

# 2. Vérification des paquets système recommandés
echo ""
echo "--- [1/5] Vérification des dépendances système Fedora ---"

MISSING_PKGS=()

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        MISSING_PKGS+=("$2")
    else
        echo "✓ Outil trouvé : $1"
    fi
}

check_cmd python3 "python3 python3-pip python3-devel"
check_cmd ffmpeg "ffmpeg"
check_cmd mpv "mpv"

# Paquets pour PyWebView (WebKitGTK)
if ! rpm -q webkit2gtk4.1 &>/dev/null && ! rpm -q webkit2gtk4.0 &>/dev/null; then
    MISSING_PKGS+=("webkit2gtk4.1")
fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo ""
    echo "⚠️ Certains paquets système sont recommandés pour une expérience optimale :"
    echo "   ${MISSING_PKGS[*]}"
    echo ""
    read -p "Souhaitez-vous exécuter 'sudo dnf install ${MISSING_PKGS[*]}' maintenant ? (o/N) : " -r INSTALL_CONFIRM
    if [[ $INSTALL_CONFIRM =~ ^[oOyY]$ ]]; then
        sudo dnf install -y "${MISSING_PKGS[@]}"
    else
        echo "ℹ Installation des paquets ignorée. Assurez-vous d'installer webkit2gtk4.1 manuellement."
    fi
else
    echo "✓ Toutes les dépendances de base sont présentes."
fi

# 3. Vérification du moteur Wayland mpvpaper (recommandé pour vidéos)
echo ""
echo "--- [2/5] Vérification du moteur vidéo Wayland (mpvpaper) ---"
if command -v mpvpaper &>/dev/null; then
    echo "✓ mpvpaper est installé et prêt."
else
    echo "ℹ mpvpaper n'est pas encore installé (recommandé pour les fonds vidéos sous Wayland)."
    echo "  Pour l'installer sur Fedora : sudo dnf install mpvpaper"
fi

# 4. Création de l'environnement virtuel Python
echo ""
echo "--- [3/5] Préparation de l'environnement Python ---"
if [ ! -d "${VENV_DIR}" ]; then
    echo "Création du virtualenv dans ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
fi

echo "Mise à niveau de pip et installation des dépendances Python..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"
echo "✓ Dépendances Python installées avec succès."

# 5. Création des dossiers utilisateur XDG
echo ""
echo "--- [4/5] Configuration des dossiers locaux ---"
mkdir -p "${HOME}/.config/wallpapermaison"
mkdir -p "${HOME}/.cache/wallpapermaison/thumbnails"
mkdir -p "${HOME}/.cache/wallpapermaison/processed"
mkdir -p "${HOME}/.cache/wallpapermaison/logs"
mkdir -p "${HOME}/Pictures/Wallpapers"
mkdir -p "${DESKTOP_FILE_DIR}"
mkdir -p "${ICON_DIR}"

# Copie de l'icône de l'application
cp "${SCRIPT_DIR}/ui/assets/logo.svg" "${ICON_DIR}/wallpapermaison.svg"
echo "✓ Icône installée dans ${ICON_DIR}/wallpapermaison.svg"

# 6. Création du raccourci de bureau .desktop
echo ""
echo "--- [5/5] Création du raccourci d'application (.desktop) ---"
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

echo "✓ Raccourci créé : ${DESKTOP_FILE}"
echo ""
echo "=========================================================="
echo "🎉 Installation terminée avec succès !"
echo "Pour lancer WallpaperMaison, vous pouvez :"
echo "  1. Cliquer sur 'WallpaperMaison' dans votre menu d'applications GNOME"
echo "  2. Ou exécuter directement : ${SCRIPT_DIR}/scripts/run.sh"
echo "=========================================================="
