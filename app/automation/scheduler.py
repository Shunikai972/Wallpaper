"""Planificateur de rotation automatique des fonds d'écran."""

import logging
import random
import threading
import time
from typing import List, Dict, Any, Optional

from app.core.config import config_manager
from app.core.events import bus
from app.storage.database import db
from app.wallpaper.manager import wallpaper_manager

logger = logging.getLogger("wallpapermaison.scheduler")

class WallpaperScheduler:
    """Gère le minuteur et la sélection du prochain fond d'écran."""

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_change_time = time.time()
        self._unseen_pool: List[int] = []
        self._history_stack: List[int] = []
        self._history_index = -1

    def is_running(self) -> bool:
        return self._running

    def get_time_remaining(self) -> int:
        """Retourne le nombre de secondes avant le prochain changement."""
        if not self._running:
            return 0
        interval = config_manager.get("auto_change.interval_seconds", 300)
        elapsed = time.time() - self._last_change_time
        return max(0, int(interval - elapsed))

    def start(self) -> None:
        """Démarre le minuteur de changement automatique."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._last_change_time = time.time()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="SchedulerThread")
            self._thread.start()
            logger.info("Changement automatique de fond d'écran activé.")
            bus.emit("scheduler_status_changed", enabled=True)

    def stop(self) -> None:
        """Arrête le minuteur."""
        with self._lock:
            self._running = False
            logger.info("Changement automatique désactivé.")
            bus.emit("scheduler_status_changed", enabled=False)

    def _loop(self) -> None:
        while self._running:
            time.sleep(1.0)
            if not self._running:
                break

            interval = config_manager.get("auto_change.interval_seconds", 300)
            elapsed = time.time() - self._last_change_time

            if elapsed >= interval:
                self._last_change_time = time.time()
                try:
                    self.next_wallpaper()
                except Exception as e:
                    logger.error("Erreur lors du changement auto de fond d'écran: %s", e)

    def _get_eligible_wallpapers(self) -> List[Dict[str, Any]]:
        """Récupère les wallpapers éligibles selon le mode et les filtres configurés."""
        mode = config_manager.get("auto_change.mode", "order")
        playlist_id = config_manager.get("auto_change.target_playlist_id")
        tags = config_manager.get("auto_change.target_tags", [])

        if playlist_id:
            pl = db.get_playlist(playlist_id)
            if pl and pl.get("items"):
                return pl["items"]

        if mode == "favorites":
            return db.get_wallpapers(favorite_only=True, limit=1000)

        if tags:
            return db.get_wallpapers(tag=tags[0] if isinstance(tags, list) else str(tags), limit=1000)

        # Par défaut, tous les wallpapers
        return db.get_wallpapers(limit=1000)

    def next_wallpaper(self) -> bool:
        """Passe au fond d'écran suivant selon la stratégie active."""
        items = self._get_eligible_wallpapers()
        if not items:
            logger.warning("Aucun fond d'écran éligible pour le changement automatique.")
            return False

        mode = config_manager.get("auto_change.mode", "order")
        item_ids = [item["id"] for item in items]
        next_id: Optional[int] = None

        # Mode aléatoire pur
        if mode == "random":
            next_id = random.choice(item_ids)

        # Mode aléatoire sans répétition
        elif mode == "random_no_repeat":
            with self._lock:
                if not self._unseen_pool:
                    self._unseen_pool = list(item_ids)
                    random.shuffle(self._unseen_pool)
                next_id = self._unseen_pool.pop()

        # Mode ordre séquentiel
        else:
            cur = wallpaper_manager.get_current_wallpaper()
            cur_id = cur.get("id") if cur else None
            if cur_id in item_ids:
                idx = item_ids.index(cur_id)
                next_id = item_ids[(idx + 1) % len(item_ids)]
            else:
                next_id = item_ids[0]

        if next_id:
            self._history_stack.append(next_id)
            self._history_index = len(self._history_stack) - 1
            self._last_change_time = time.time()
            return wallpaper_manager.apply_wallpaper(next_id)

        return False

    def previous_wallpaper(self) -> bool:
        """Revient au fond d'écran précédent."""
        if len(self._history_stack) > 1 and self._history_index > 0:
            self._history_index -= 1
            prev_id = self._history_stack[self._history_index]
            self._last_change_time = time.time()
            return wallpaper_manager.apply_wallpaper(prev_id)
        return False

scheduler = WallpaperScheduler()
