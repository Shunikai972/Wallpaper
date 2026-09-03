"""Détection de l'environnement Linux Fedora, du serveur d'affichage et des outils disponibles."""

import logging
import os
import shutil
import subprocess
from typing import Dict, Any, List

logger = logging.getLogger("wallpapermaison.detector")

class SystemDetector:
    """Analyse l'environnement hôte Linux."""
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def detect_all(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Détecte l'ensemble des caractéristiques du système et des outils disponibles."""
        if self._cache and not force_refresh:
            return self._cache.copy()

        distro_info = self._detect_distro()
        session_type = self._detect_session_type()
        desktop_env = self._detect_desktop_environment()
        tools = self._detect_available_tools()
        recommended_engine = self._determine_recommended_engine(desktop_env, session_type, tools)

        res = {
            "distro": distro_info,
            "session_type": session_type, # "wayland" ou "x11"
            "desktop_env": desktop_env,   # "gnome", "kde", "sway", "hyprland", "xfce", "other"
            "tools": tools,
            "recommended_engine": recommended_engine,
            "capabilities": {
                "can_static": True,
                "can_video": bool(tools.get("mpvpaper") or tools.get("xwinwrap") or (desktop_env == "gnome") or (desktop_env == "kde")),
                "can_gif": bool(tools.get("swww") or tools.get("mpvpaper") or tools.get("xwinwrap")),
                "has_hardware_accel": bool(tools.get("mpv") or tools.get("ffmpeg"))
            }
        }
        self._cache = res
        logger.info("Détection système: Distro=%s, Session=%s, DE=%s, Moteur recommandé=%s",
                    distro_info.get("pretty_name"), session_type, desktop_env, recommended_engine)
        return res

    def _detect_distro(self) -> Dict[str, str]:
        """Lit /etc/os-release pour identifier la distribution (ex: Fedora 39/40/41)."""
        info = {
            "id": "unknown",
            "name": "Linux",
            "version": "",
            "pretty_name": "Linux",
            "is_fedora": False
        }
        os_release = "/etc/os-release"
        if os.path.exists(os_release):
            try:
                with open(os_release, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        v = v.strip('"\'')
                        if k == "ID":
                            info["id"] = v.lower()
                        elif k == "NAME":
                            info["name"] = v
                        elif k == "VERSION_ID":
                            info["version"] = v
                        elif k == "PRETTY_NAME":
                            info["pretty_name"] = v
                info["is_fedora"] = "fedora" in info["id"] or "fedora" in info["name"].lower()
            except Exception as e:
                logger.warning("Erreur lors de la lecture de /etc/os-release: %s", e)
        return info

    def _detect_session_type(self) -> str:
        """Détecte si la session courante est Wayland ou X11."""
        sess = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if "wayland" in sess or os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if "x11" in sess or os.environ.get("DISPLAY"):
            return "x11"
        return "wayland" if os.environ.get("WAYLAND_DISPLAY") else "unknown"

    def _detect_desktop_environment(self) -> str:
        """Détecte l'environnement de bureau actif (GNOME, KDE Plasma, etc.)."""
        xdg_de = (os.environ.get("XDG_CURRENT_DESKTOP", "") + ":" + os.environ.get("DESKTOP_SESSION", "")).lower()
        if "gnome" in xdg_de:
            return "gnome"
        if "kde" in xdg_de or "plasma" in xdg_de:
            return "kde"
        if "hyprland" in xdg_de:
            return "hyprland"
        if "sway" in xdg_de:
            return "sway"
        if "xfce" in xdg_de:
            return "xfce"
        return "generic"

    def _detect_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Vérifie la présence des exécutables et propose les commandes Fedora d'installation."""
        tools_to_check = {
            "gsettings": {
                "desc": "Configuration GNOME native (GSettings)",
                "package_fedora": "glib2",
                "install_cmd": "sudo dnf install glib2"
            },
            "qdbus": {
                "desc": "Contrôle DBus KDE Plasma",
                "package_fedora": "qt5-qdbus ou qt6-qdbus",
                "install_cmd": "sudo dnf install qt6-qdbus"
            },
            "mpvpaper": {
                "desc": "Moteur vidéo fluide pour Wayland",
                "package_fedora": "mpvpaper",
                "install_cmd": "sudo dnf install mpvpaper"
            },
            "swww": {
                "desc": "Moteur animé et transitions pour Wayland",
                "package_fedora": "swww",
                "install_cmd": "cargo install swww ou via COPR"
            },
            "swaybg": {
                "desc": "Fonds d'écran statiques pour Sway/Wayland",
                "package_fedora": "swaybg",
                "install_cmd": "sudo dnf install swaybg"
            },
            "hyprpaper": {
                "desc": "Moteur statique pour Hyprland",
                "package_fedora": "hyprpaper",
                "install_cmd": "sudo dnf install hyprpaper"
            },
            "feh": {
                "desc": "Fonds statiques légers pour sessions X11",
                "package_fedora": "feh",
                "install_cmd": "sudo dnf install feh"
            },
            "xwinwrap": {
                "desc": "Lecteur vidéo plein écran X11 sur root window",
                "package_fedora": "xwinwrap",
                "install_cmd": "sudo dnf install xwinwrap"
            },
            "mpv": {
                "desc": "Lecteur multimédia avec accélération matérielle",
                "package_fedora": "mpv",
                "install_cmd": "sudo dnf install mpv"
            },
            "ffmpeg": {
                "desc": "Extraction de miniatures et conversion vidéo",
                "package_fedora": "ffmpeg",
                "install_cmd": "sudo dnf install ffmpeg (RPM Fusion)"
            },
            "ffprobe": {
                "desc": "Analyse technique des métadonnées vidéo",
                "package_fedora": "ffmpeg",
                "install_cmd": "sudo dnf install ffmpeg (RPM Fusion)"
            },
            "upower": {
                "desc": "Gestion et détection de la batterie / secteur",
                "package_fedora": "upower",
                "install_cmd": "sudo dnf install upower"
            }
        }

        result = {}
        for tool, meta in tools_to_check.items():
            path = shutil.which(tool)
            result[tool] = {
                "installed": bool(path),
                "path": path or "",
                "description": meta["desc"],
                "package_fedora": meta["package_fedora"],
                "install_cmd": meta["install_cmd"]
            }
        return result

    def _determine_recommended_engine(self, de: str, session: str, tools: Dict[str, Dict[str, Any]]) -> str:
        """Choisit intelligemment le moteur par défaut selon le DE et la session."""
        if session == "wayland":
            if tools.get("mpvpaper", {}).get("installed"):
                return "mpvpaper"
            if de == "gnome" and tools.get("gsettings", {}).get("installed"):
                return "gnome"
            if de == "kde":
                return "kde"
            if tools.get("swww", {}).get("installed"):
                return "swww"
            return "gnome" if de == "gnome" else "fallback"
        else: # X11
            if de == "gnome" and tools.get("gsettings", {}).get("installed"):
                return "gnome"
            if de == "kde":
                return "kde"
            if tools.get("feh", {}).get("installed"):
                return "feh"
            return "xwinwrap" if tools.get("xwinwrap", {}).get("installed") else "fallback"

system_detector = SystemDetector()
