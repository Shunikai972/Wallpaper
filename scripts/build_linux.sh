#!/usr/bin/env bash
# ==============================================================================
# Script de compilation binaire standalone pour Linux (Fedora, Ubuntu, etc.)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

BUILD_VENV="/tmp/wm_build_venv"
DIST_DIR="${SCRIPT_DIR}/dist"
BUILD_DIR="${SCRIPT_DIR}/build"

echo "=========================================================="
echo "    Compilation binaire de WallpaperMaison pour Linux     "
echo "=========================================================="
echo "Répertoire racine : ${SCRIPT_DIR}"
echo "Système hôte : $(uname -s) $(uname -m)"
echo ""

# 1. Vérification de Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Erreur : python3 est introuvable."
    exit 1
fi

# 2. Préparation du virtualenv de compilation
echo "--- [1/4] Préparation de l'environnement de compilation isolé ---"
rm -rf "${BUILD_VENV}"
python3 -m venv "${BUILD_VENV}"
"${BUILD_VENV}/bin/pip" install --upgrade pip setuptools wheel

# 3. Installation des dépendances et de PyInstaller
echo "--- [2/4] Installation des dépendances et de PyInstaller ---"
"${BUILD_VENV}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"
"${BUILD_VENV}/bin/pip" install "pyinstaller>=6.4.0"

# 4. Compilation via PyInstaller
echo "--- [3/4] Exécution de PyInstaller avec wallpapermaison.spec ---"
rm -rf "${DIST_DIR}" "${BUILD_DIR}"
"${BUILD_VENV}/bin/pyinstaller" --clean "${SCRIPT_DIR}/wallpapermaison.spec"

# 5. Finalisation et création de l'archive tar.gz
echo "--- [4/4] Finalisation et permissions ---"
chmod +x "${DIST_DIR}/wallpapermaison/wallpapermaison"

TAR_NAME="wallpapermaison-linux-x86_64.tar.gz"
cd "${DIST_DIR}"
tar -czf "${TAR_NAME}" wallpapermaison

echo ""
echo "=========================================================="
echo "🎉 Compilation terminée avec succès !"
echo "Exécutable autonome disponible dans :"
echo "  👉 ${DIST_DIR}/wallpapermaison/wallpapermaison"
echo ""
echo "Archive portable générée :"
echo "  👉 ${DIST_DIR}/${TAR_NAME} ($(du -h "${TAR_NAME}" | cut -f1))"
echo "=========================================================="
