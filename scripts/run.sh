#!/usr/bin/env bash
# ==============================================================================
# Script de lancement pour WallpaperMaison
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Si le virtualenv existe, on l'utilise, sinon python3 système
if [ -x "${VENV_PYTHON}" ]; then
    PYTHON_EXEC="${VENV_PYTHON}"
else
    PYTHON_EXEC="python3"
fi

export PATH="${HOME}/.local/bin:${SCRIPT_DIR}/scripts:${PATH}"
export PYSTRAY_BACKEND="${PYSTRAY_BACKEND:-xorg}"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Lancement de l'application
exec "${PYTHON_EXEC}" "${SCRIPT_DIR}/app/main.py" "$@"
