import json
import logging
import os
import random
import threading
import time
from pathlib import Path
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

    def _get_rotation_config(self) -> Dict[str, Any]:
        """Charge les réglages de rotation automatique depuis rotation_settings.json ou .env."""
        res = {
            "enabled": config_manager.get("auto_change.enabled", False),
            "interval_seconds": config_manager.get("auto_change.interval_seconds", 300),
            "folder": "",
            "order": config_manager.get("auto_change.mode", "random")
        }
        # 1. Lecture des fichiers de configuration JSON
        for sp in [
            Path.home() / ".config/wallpapermaison/rotation_settings.json",
            Path.home() / "reseau/Perso/.config/wallpapermaison/rotation_settings.json"
        ]:
            if sp.exists():
                try:
                    data = json.loads(sp.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        if "enabled" in data:
                            res["enabled"] = bool(data["enabled"])
                        if "intervalMinutes" in data and isinstance(data["intervalMinutes"], (int, float)):
                            res["interval_seconds"] = max(10, int(data["intervalMinutes"] * 60))
                        elif "interval_minutes" in data and isinstance(data["interval_minutes"], (int, float)):
                            res["interval_seconds"] = max(10, int(data["interval_minutes"] * 60))
                        if data.get("folder") and os.path.isdir(str(data["folder"])):
                            res["folder"] = str(data["folder"])
                        if data.get("order"):
                            res["order"] = str(data["order"])
                        break
                except Exception:
                    pass

        # 2. Compléter / Surcharger via .env
        for ep in [
            Path(__file__).resolve().parents[2] / ".env",
            Path.home() / "reseau/Perso/Bureau/Wallpaper/.env",
            Path.home() / "Bureau/Wallpaper/.env"
        ]:
            if ep.exists():
                try:
                    for line in ep.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip().upper()
                        v = v.strip().strip("'\"")
                        if k == "ROTATION_ENABLED":
                            res["enabled"] = v.lower() in ("true", "1", "yes")
                        elif k == "ROTATION_INTERVAL_MINUTES":
                            try:
                                res["interval_seconds"] = max(10, int(float(v) * 60))
                            except ValueError:
                                pass
                        elif k == "ROTATION_FOLDER" and os.path.isdir(v):
                            res["folder"] = v
                        elif k == "ROTATION_ORDER":
                            res["order"] = v.lower()
                    break
                except Exception:
                    pass

        return res

    def is_running(self) -> bool:
        return self._running

    def get_time_remaining(self) -> int:
        """Retourne le nombre de secondes avant le prochain changement."""
        if not self._running:
            return 0
        cfg = self._get_rotation_config()
        interval = cfg.get("interval_seconds", 300)
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

            cfg = self._get_rotation_config()
            interval = cfg.get("interval_seconds", 300)

            # Vérifier si VS Code ou un autre processus a appliqué un wallpaper récemment
            state_file = Path.home() / ".config/wallpapermaison/current_wallpaper.json"
            if state_file.exists():
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    ts = float(data.get("timestamp", 0))
                    if ts > self._last_change_time:
                        self._last_change_time = ts
                except Exception:
                    pass

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
        cfg = self._get_rotation_config()
        folder = cfg.get("folder")
        order = cfg.get("order", "random")
        if order == "sequential":
            order = "order"

        # 1. Si un dossier spécifique est configuré pour la rotation
        if folder and os.path.isdir(folder):
            valid_exts = {".mp4", ".webm", ".mkv", ".mov", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
            folder_files = []
            try:
                for entry in os.scandir(folder):
                    if (entry.is_file() or entry.is_symlink()) and not entry.name.startswith(".") and not entry.name.endswith(".part") and entry.name != "wallpaper.mp4":
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in valid_exts:
                            folder_files.append(entry.path)
            except Exception as e:
                logger.warning("Erreur scan dossier rotation %s: %s", folder, e)

            if folder_files:
                folder_files.sort()
                cur = wallpaper_manager.get_current_wallpaper()
                cur_path = cur.get("file_path", "") if cur else ""
                chosen_path = None
                if order == "random":
                    pool = [p for p in folder_files if p != cur_path] or folder_files
                    chosen_path = random.choice(pool)
                else:
                    if cur_path in folder_files:
                        idx = folder_files.index(cur_path)
                        chosen_path = folder_files[(idx + 1) % len(folder_files)]
                    else:
                        chosen_path = folder_files[0]

                if chosen_path:
                    self._last_change_time = time.time()
                    return wallpaper_manager.apply_wallpaper_by_path(chosen_path)

        # 2. Fallback sur la bibliothèque de base de données
        items = self._get_eligible_wallpapers()
        if not items:
            logger.warning("Aucun fond d'écran éligible pour le changement automatique.")
            return False

        item_ids = [item["id"] for item in items]
        next_id: Optional[int] = None

        # Mode aléatoire pur
        if order == "random":
            next_id = random.choice(item_ids)

        # Mode aléatoire sans répétition
        elif order == "random_no_repeat":
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

