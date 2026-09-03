"""Moteur d'automatisations et de règles contextuelles."""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.core.config import config_manager
from app.core.events import bus
from app.storage.database import db
from app.wallpaper.manager import wallpaper_manager

logger = logging.getLogger("wallpapermaison.rules")

class RuleEngine:
    """Évalue et déclenche les règles automatisées (heures, batterie, plein écran)."""

    def __init__(self, interval: float = 30.0) -> None:
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_minute_checked = ""

        bus.subscribe("power_changed", self._handle_power_event)
        bus.subscribe("fullscreen_state_changed", self._handle_fullscreen_event)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="RuleEngineThread")
        self._thread.start()
        logger.info("Moteur d'automatisations démarré.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Moteur d'automatisations arrêté.")

    def _loop(self) -> None:
        while self._running:
            try:
                now_str = datetime.now().strftime("%H:%M")
                if now_str != self._last_minute_checked:
                    self._last_minute_checked = now_str
                    self._check_time_rules(now_str)
            except Exception as e:
                logger.error("Erreur évaluation des règles horaires: %s", e)
            time.sleep(self.interval)

    def _check_time_rules(self, current_time: str) -> None:
        rules = db.get_automations()
        for r in rules:
            if r["is_enabled"] and r["trigger_type"] == "time" and r["trigger_condition"] == current_time:
                logger.info("Déclenchement de la règle horaire '%s' (%s)", r["name"], current_time)
                self.execute_action(r["action_type"], r["action_target"])

    def _handle_power_event(self, on_battery: bool, percentage: float) -> None:
        rules = db.get_automations()
        for r in rules:
            if not r["is_enabled"]:
                continue
            if on_battery and r["trigger_type"] == "battery":
                logger.info("Déclenchement de la règle sur batterie: %s", r["name"])
                self.execute_action(r["action_type"], r["action_target"])
            elif not on_battery and r["trigger_type"] == "ac_power":
                logger.info("Déclenchement de la règle sur secteur: %s", r["name"])
                self.execute_action(r["action_type"], r["action_target"])

    def _handle_fullscreen_event(self, is_fullscreen: bool) -> None:
        rules = db.get_automations()
        for r in rules:
            if not r["is_enabled"]:
                continue
            if is_fullscreen and r["trigger_type"] == "fullscreen":
                logger.info("Déclenchement de la règle plein écran: %s", r["name"])
                self.execute_action(r["action_type"], r["action_target"])

    def execute_action(self, action_type: str, action_target: str) -> None:
        """Exécute l'action demandée par une règle."""
        try:
            if action_type == "set_profile":
                config_manager.set("performance_profile", action_target)
                logger.info("Profil de performance changé par automation: %s", action_target)

            elif action_type == "set_playlist":
                playlists = db.get_playlists()
                target_pl = next((p for p in playlists if p["name"].lower() == action_target.lower()), None)
                if target_pl:
                    config_manager.set("auto_change.target_playlist_id", target_pl["id"])
                    pl_full = db.get_playlist(target_pl["id"])
                    if pl_full and pl_full.get("items"):
                        wallpaper_manager.apply_wallpaper(pl_full["items"][0]["id"])
                    logger.info("Playlist activée par automation: %s", target_pl["name"])

            elif action_type == "pause_video":
                wallpaper_manager.pause()

            elif action_type == "resume_video":
                wallpaper_manager.resume()

            elif action_type == "set_wallpaper":
                wp_id = int(action_target)
                wallpaper_manager.apply_wallpaper(wp_id)

        except Exception as e:
            logger.error("Erreur lors de l'exécution de l'action %s (%s): %s", action_type, action_target, e)

rule_engine = RuleEngine()
