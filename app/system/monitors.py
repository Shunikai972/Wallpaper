"""Détection et gestion multi-moniteurs sous Linux Fedora (Wayland & X11)."""

import logging
import os
import re
import shutil
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger("wallpapermaison.monitors")

class MonitorDetector:
    """Détecte les écrans connectés, leurs résolutions, refresh rates et statuts."""
    def __init__(self) -> None:
        self._cached_monitors: List[Dict[str, Any]] = []

    def get_monitors(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Retourne la liste des écrans détectés."""
        if self._cached_monitors and not force_refresh:
            return self._cached_monitors

        monitors = []
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()

        # 1. Tentative via wlr-randr si sous Wayland
        if "wayland" in session and shutil.which("wlr-randr"):
            monitors = self._parse_wlr_randr()

        # 2. Tentative via xrandr (compatible X11 et souvent Xwayland)
        if not monitors and shutil.which("xrandr"):
            monitors = self._parse_xrandr()

        # 3. Tentative via kscreen-doctor (KDE Plasma)
        if not monitors and shutil.which("kscreen-doctor"):
            monitors = self._parse_kscreen()

        # 4. Fallback sysfs DRM sous Linux
        if not monitors:
            monitors = self._parse_drm_sysfs()

        # 5. Fallback par défaut si aucune commande ne répond (ex. test ou VM sans outils)
        if not monitors:
            monitors = [{
                "id": "DP-1",
                "name": "Écran Principal",
                "connector": "DP-1",
                "width": 1920,
                "height": 1080,
                "refresh_rate": 60.0,
                "is_primary": True,
                "x": 0,
                "y": 0,
                "scale": 1.0
            }]

        self._cached_monitors = monitors
        logger.info("Écrans détectés (%d): %s", len(monitors), [m["name"] for m in monitors])
        return monitors

    def _parse_xrandr(self) -> List[Dict[str, Any]]:
        monitors = []
        try:
            output = subprocess.check_output(["xrandr", "--query"], stderr=subprocess.DEVNULL, text=True, timeout=3)
            # Motif typique: DP-1 connected primary 1920x1080+0+0 (normal left inverted right ...) 527mm x 296mm
            pattern = re.compile(
                r"^(\S+)\s+connected\s+(primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)"
            )
            rate_pattern = re.compile(r"(\d+\.\d+)\*")

            current_mon: Optional[Dict[str, Any]] = None

            for line in output.splitlines():
                match = pattern.match(line)
                if match:
                    connector = match.group(1)
                    is_primary = bool(match.group(2))
                    w = int(match.group(3))
                    h = int(match.group(4))
                    x = int(match.group(5))
                    y = int(match.group(6))
                    current_mon = {
                        "id": connector,
                        "name": connector,
                        "connector": connector,
                        "width": w,
                        "height": h,
                        "refresh_rate": 60.0,
                        "is_primary": is_primary,
                        "x": x,
                        "y": y,
                        "scale": 1.0
                    }
                    monitors.append(current_mon)
                elif current_mon and "*" in line:
                    r_match = rate_pattern.search(line)
                    if r_match:
                        current_mon["refresh_rate"] = float(r_match.group(1))

            # Si aucun n'est marqué primary, le premier l'est par défaut
            if monitors and not any(m["is_primary"] for m in monitors):
                monitors[0]["is_primary"] = True

        except Exception as e:
            logger.debug("Erreur lors de l'exécution de xrandr: %s", e)
        return monitors

    def _parse_wlr_randr(self) -> List[Dict[str, Any]]:
        monitors = []
        try:
            output = subprocess.check_output(["wlr-randr"], stderr=subprocess.DEVNULL, text=True, timeout=3)
            # wlr-randr produit un bloc par écran
            current_id = ""
            for line in output.splitlines():
                line_str = line.strip()
                if not line.startswith(" "):
                    current_id = line.split()[0]
                elif "current" in line_str and current_id:
                    # ex: "1920x1080 px, 60.000000 Hz (current)"
                    parts = line_str.split(",")
                    res = parts[0].replace("px", "").strip().split("x")
                    hz = 60.0
                    if len(parts) > 1 and "Hz" in parts[1]:
                        hz_str = parts[1].replace("Hz", "").replace("(current)", "").strip()
                        try:
                            hz = round(float(hz_str), 1)
                        except ValueError:
                            pass
                    monitors.append({
                        "id": current_id,
                        "name": current_id,
                        "connector": current_id,
                        "width": int(res[0]),
                        "height": int(res[1]),
                        "refresh_rate": hz,
                        "is_primary": len(monitors) == 0,
                        "x": 0,
                        "y": 0,
                        "scale": 1.0
                    })
                    current_id = ""
        except Exception as e:
            logger.debug("Erreur wlr-randr: %s", e)
        return monitors

    def _parse_kscreen(self) -> List[Dict[str, Any]]:
        monitors = []
        try:
            output = subprocess.check_output(["kscreen-doctor", "-o"], stderr=subprocess.DEVNULL, text=True, timeout=3)
            # kscreen-doctor liste Output 1: ...
            for line in output.splitlines():
                if "Output" in line and "connected" in line:
                    parts = line.split()
                    name = parts[2] if len(parts) > 2 else "Screen"
                    res_match = re.search(r"(\d+)x(\d+)@(\d+)", line)
                    if res_match:
                        w, h, rate = int(res_match.group(1)), int(res_match.group(2)), float(res_match.group(3))
                        monitors.append({
                            "id": name,
                            "name": name,
                            "connector": name,
                            "width": w,
                            "height": h,
                            "refresh_rate": rate,
                            "is_primary": "primary" in line.lower() or len(monitors) == 0,
                            "x": 0,
                            "y": 0,
                            "scale": 1.0
                        })
        except Exception as e:
            logger.debug("Erreur kscreen-doctor: %s", e)
        return monitors

    def _parse_drm_sysfs(self) -> List[Dict[str, Any]]:
        monitors = []
        drm_path = "/sys/class/drm"
        if not os.path.exists(drm_path):
            return monitors

        try:
            for item in os.listdir(drm_path):
                status_file = os.path.join(drm_path, item, "status")
                if os.path.isfile(status_file):
                    with open(status_file, "r") as f:
                        if f.read().strip() == "connected":
                            conn_name = item.replace("card0-", "").replace("card1-", "")
                            # Lecture modes si disponible
                            modes_file = os.path.join(drm_path, item, "modes")
                            w, h = 1920, 1080
                            if os.path.isfile(modes_file):
                                with open(modes_file, "r") as mf:
                                    first_mode = mf.readline().strip()
                                    if "x" in first_mode:
                                        m_parts = first_mode.split("x")
                                        w, h = int(m_parts[0]), int(m_parts[1])
                            monitors.append({
                                "id": conn_name,
                                "name": conn_name,
                                "connector": conn_name,
                                "width": w,
                                "height": h,
                                "refresh_rate": 60.0,
                                "is_primary": len(monitors) == 0,
                                "x": 0,
                                "y": 0,
                                "scale": 1.0
                            })
        except Exception as e:
            logger.debug("Erreur sysfs DRM: %s", e)
        return monitors

    def get_bounding_box(self) -> Dict[str, int]:
        """Calcule la géométrie totale de l'ensemble des moniteurs (pour mode étendu)."""
        monitors = self.get_monitors()
        if not monitors:
            return {"width": 1920, "height": 1080}
        total_w = sum(m["width"] for m in monitors)
        max_h = max(m["height"] for m in monitors)
        return {"width": total_w, "height": max_h}

monitor_detector = MonitorDetector()
