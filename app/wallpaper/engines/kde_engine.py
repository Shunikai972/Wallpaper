"""Moteur de fond d'écran KDE Plasma via DBus / plasmashell."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.wallpaper.base import BaseWallpaperEngine

logger = logging.getLogger("wallpapermaison.engine.kde")

class KdeWallpaperEngine(BaseWallpaperEngine):
    """Contrôle les fonds d'écran sur KDE Plasma via evaluateScript."""

    @property
    def name(self) -> str:
        return "kde"

    @property
    def display_name(self) -> str:
        return "KDE Plasma (DBus Script)"

    @property
    def supported_types(self) -> List[str]:
        return ["image", "gif"]

    def is_available(self) -> bool:
        has_qdbus = bool(shutil.which("qdbus") or shutil.which("qdbus-qt5") or shutil.which("qdbus-qt6"))
        is_kde = "kde" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower() or "plasma" in os.environ.get("DESKTOP_SESSION", "").lower()
        return has_qdbus and is_kde

    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        p = Path(wallpaper_path).resolve()
        if not p.exists():
            return False

        qdbus_bin = shutil.which("qdbus-qt6") or shutil.which("qdbus") or shutil.which("qdbus-qt5")
        if not qdbus_bin:
            return False

        file_uri = f"file://{p}"
        # Script JS pour plasmashell
        js_script = f"""
        var allDesktops = desktops();
        for (var i = 0; i < allDesktops.length; i++) {{
            var d = allDesktops[i];
            d.wallpaperPlugin = "org.kde.image";
            d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
            d.writeConfig("Image", "{file_uri}");
        }}
        """

        try:
            subprocess.run([
                qdbus_bin, "org.kde.plasmashell", "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript", js_script
            ], check=True, timeout=4)
            logger.info("Fond d'écran appliqué via KDE Plasma: %s", p.name)
            return True
        except Exception as e:
            logger.error("Erreur application KDE Plasma: %s", e)
            return False
