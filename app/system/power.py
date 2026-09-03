"""Surveillance de l'état de l'alimentation (secteur / batterie) sous Linux Fedora."""

import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Dict, Any, Optional

from app.core.events import bus

logger = logging.getLogger("wallpapermaison.power")

class PowerMonitor:
    """Surveille les changements d'état batterie / alimentation secteur."""
    def __init__(self, check_interval: float = 10.0) -> None:
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_state: Dict[str, Any] = {"on_battery": False, "percentage": 100.0, "has_battery": False}

    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel de l'alimentation."""
        # 1. Vérification /sys/class/power_supply
        status = self._check_sysfs()
        if status is not None:
            self._last_state = status
            return status

        # 2. Vérification upower
        if shutil.which("upower"):
            status = self._check_upower()
            if status is not None:
                self._last_state = status
                return status

        # Fallback si PC de bureau sans batterie
        return {"on_battery": False, "percentage": 100.0, "has_battery": False}

    def _check_sysfs(self) -> Optional[Dict[str, Any]]:
        ps_path = "/sys/class/power_supply"
        if not os.path.exists(ps_path):
            return None

        has_battery = False
        on_battery = False
        percentage = 100.0

        try:
            for item in os.listdir(ps_path):
                type_file = os.path.join(ps_path, item, "type")
                if os.path.exists(type_file):
                    with open(type_file, "r") as f:
                        ps_type = f.read().strip().lower()

                    if ps_type == "battery":
                        has_battery = True
                        status_file = os.path.join(ps_path, item, "status")
                        if os.path.exists(status_file):
                            with open(status_file, "r") as sf:
                                st = sf.read().strip().lower()
                                if st in ["discharging"]:
                                    on_battery = True

                        capacity_file = os.path.join(ps_path, item, "capacity")
                        if os.path.exists(capacity_file):
                            with open(capacity_file, "r") as cf:
                                percentage = float(cf.read().strip())

            if has_battery:
                return {
                    "on_battery": on_battery,
                    "percentage": percentage,
                    "has_battery": True
                }
        except Exception as e:
            logger.debug("Erreur lecture sysfs power_supply: %s", e)
        return None

    def _check_upower(self) -> Optional[Dict[str, Any]]:
        try:
            out = subprocess.check_output(
                ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
                stderr=subprocess.DEVNULL, text=True, timeout=2
            )
            on_battery = "state:               discharging" in out or "state: discharging" in out
            pct = 100.0
            for line in out.splitlines():
                if "percentage:" in line:
                    p_str = line.split(":")[-1].replace("%", "").strip()
                    pct = float(p_str)
                    break
            return {"on_battery": on_battery, "percentage": pct, "has_battery": True}
        except Exception:
            return None

    def start(self) -> None:
        """Démarre le thread de surveillance périodique."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="PowerMonitorThread")
        self._thread.start()
        logger.info("Surveillance de l'alimentation démarrée.")

    def stop(self) -> None:
        """Arrête la surveillance."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Surveillance de l'alimentation arrêtée.")

    def _poll_loop(self) -> None:
        last_battery_state = None
        while self._running:
            try:
                current = self.get_status()
                if current.get("has_battery"):
                    cur_battery = current.get("on_battery")
                    if last_battery_state is not None and cur_battery != last_battery_state:
                        logger.info("Changement d'état d'alimentation détecté: sur batterie = %s", cur_battery)
                        bus.emit("power_changed", on_battery=cur_battery, percentage=current.get("percentage"))
                    last_battery_state = cur_battery
            except Exception as e:
                logger.error("Erreur dans la boucle PowerMonitor: %s", e)
            time.sleep(self.check_interval)

power_monitor = PowerMonitor()
