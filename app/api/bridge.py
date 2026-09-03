"""Passerelle API Python ↔ JavaScript pour PyWebView."""

import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.automation.rules import rule_engine
from app.automation.scheduler import scheduler
from app.core.config import config_manager, PERFORMANCE_PROFILES
from app.core.logger import get_recent_logs
from app.image_processing.adjuster import image_adjuster
from app.media.scanner import media_scanner
from app.storage.cache import cache_manager
from app.storage.database import db
from app.system.autostart import autostart_manager
from app.system.detector import system_detector
from app.system.monitors import monitor_detector
from app.system.power import power_monitor
from app.wallpaper.manager import wallpaper_manager

logger = logging.getLogger("wallpapermaison.bridge")

class AppBridge:
    """Expose les services Python au frontend JavaScript via PyWebView."""

    def __init__(self, window=None) -> None:
        self.window = window

    def set_window(self, window) -> None:
        self.window = window

    # --- Bibliothèque & Wallpapers ---
    def get_wallpapers(self, search: str = "", media_type: str = "all", favorite_only: bool = False,
                       tag: str = "", sort_by: str = "created_desc", limit: int = 500, offset: int = 0) -> Dict[str, Any]:
        try:
            items = db.get_wallpapers(search=search, media_type=media_type, favorite_only=favorite_only,
                                      tag=tag, sort_by=sort_by, limit=limit, offset=offset)
            return {"success": True, "data": items}
        except Exception as e:
            logger.error("Erreur get_wallpapers: %s", e)
            return {"success": False, "error": str(e)}

    def get_wallpaper_by_id(self, wallpaper_id: int) -> Dict[str, Any]:
        try:
            wp = db.get_wallpaper_by_id(wallpaper_id)
            if not wp:
                return {"success": False, "error": "Fond introuvable"}
            return {"success": True, "data": wp}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def toggle_favorite(self, wallpaper_id: int) -> Dict[str, Any]:
        try:
            new_state = db.toggle_favorite(wallpaper_id)
            return {"success": True, "is_favorite": new_state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_tags(self, wallpaper_id: int, tags: str) -> Dict[str, Any]:
        try:
            db.update_tags(wallpaper_id, tags)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_wallpaper(self, wallpaper_id: int) -> Dict[str, Any]:
        try:
            success = db.delete_wallpaper(wallpaper_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_tags(self) -> Dict[str, Any]:
        try:
            tags = db.get_all_tags()
            return {"success": True, "data": tags}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        try:
            stats = db.get_stats()
            return {"success": True, "data": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Scanner & Import ---
    def start_scan(self, directories: Optional[List[str]] = None, recursive: bool = True) -> Dict[str, Any]:
        try:
            if directories is None:
                directories = config_manager.get("library_folders", [])
            media_scanner.scan_directories_async(directories, recursive=recursive)
            return {"success": True, "message": "Scan démarré en arrière-plan"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def abort_scan(self) -> Dict[str, Any]:
        media_scanner.abort()
        return {"success": True}

    def is_scanning(self) -> Dict[str, Any]:
        return {"success": True, "is_scanning": media_scanner.is_scanning()}

    def import_single_file(self, file_path: str) -> Dict[str, Any]:
        try:
            res = media_scanner.import_single_file(file_path)
            if res:
                return {"success": True, "data": res}
            return {"success": False, "error": "Type de fichier non supporté ou introuvable"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_directory_dialog(self) -> Dict[str, Any]:
        """Ouvre un dialogue de sélection de dossier natif."""
        if not self.window:
            return {"success": False, "error": "Fenêtre principale non initialisée"}
        try:
            import webview
            result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                folder = result[0]
                return {"success": True, "folder": folder}
            return {"success": False, "cancelled": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_file_dialog(self) -> Dict[str, Any]:
        """Ouvre un dialogue de sélection de fichiers images/vidéos."""
        if not self.window:
            return {"success": False, "error": "Fenêtre principale non initialisée"}
        try:
            import webview
            file_types = ("Fichiers multimédias (*.png;*.jpg;*.jpeg;*.webp;*.gif;*.mp4;*.webm;*.mkv)", "Tous les fichiers (*.*)")
            result = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
            if result:
                imported = []
                for p in result:
                    res = media_scanner.import_single_file(p)
                    if res:
                        imported.append(res)
                return {"success": True, "imported_count": len(imported), "data": imported}
            return {"success": False, "cancelled": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Contrôle des Fonds d'Écran ---
    def apply_wallpaper(self, wallpaper_id: int, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            success = wallpaper_manager.apply_wallpaper(wallpaper_id, monitor=monitor, options=options)
            cur = wallpaper_manager.get_current_wallpaper(monitor)
            return {"success": success, "current": cur}
        except Exception as e:
            logger.error("Erreur apply_wallpaper: %s", e)
            return {"success": False, "error": str(e)}

    def get_current_wallpaper(self, monitor: str = "all") -> Dict[str, Any]:
        try:
            cur = wallpaper_manager.get_current_wallpaper(monitor)
            return {"success": True, "data": cur}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pause_wallpaper(self, monitor: str = "all") -> Dict[str, Any]:
        success = wallpaper_manager.pause(monitor)
        return {"success": success}

    def resume_wallpaper(self, monitor: str = "all") -> Dict[str, Any]:
        success = wallpaper_manager.resume(monitor)
        return {"success": success}

    def next_wallpaper(self) -> Dict[str, Any]:
        success = scheduler.next_wallpaper()
        return {"success": success}

    def previous_wallpaper(self) -> Dict[str, Any]:
        success = scheduler.previous_wallpaper()
        return {"success": success}

    def get_engines_status(self) -> Dict[str, Any]:
        try:
            return {"success": True, "data": wallpaper_manager.get_engines_status()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Éditeur d'Image Non Destructif ---
    def get_adjustments(self, wallpaper_id: int) -> Dict[str, Any]:
        try:
            adj = db.get_adjustments(wallpaper_id)
            return {"success": True, "data": adj or {}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_adjustments(self, wallpaper_id: int, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            db.save_adjustments(wallpaper_id, adjustments)
            # Régénération du rendu pour application immédiate si c'est le wallpaper actuel
            cur = wallpaper_manager.get_current_wallpaper()
            if cur and cur.get("id") == wallpaper_id:
                wallpaper_manager.apply_wallpaper(wallpaper_id)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reset_adjustments(self, wallpaper_id: int) -> Dict[str, Any]:
        try:
            db.reset_adjustments(wallpaper_id)
            cur = wallpaper_manager.get_current_wallpaper()
            if cur and cur.get("id") == wallpaper_id:
                wallpaper_manager.apply_wallpaper(wallpaper_id)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Playlists ---
    def get_playlists(self) -> Dict[str, Any]:
        try:
            return {"success": True, "data": db.get_playlists()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        try:
            pl = db.get_playlist(playlist_id)
            if not pl:
                return {"success": False, "error": "Playlist introuvable"}
            return {"success": True, "data": pl}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_playlist(self, name: str, description: str = "", icon: str = "folder", interval: int = 300, is_random: int = 0) -> Dict[str, Any]:
        try:
            pid = db.create_playlist(name, description, icon, interval, is_random)
            return {"success": True, "id": pid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_playlist(self, playlist_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            db.update_playlist(playlist_id, data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_playlist(self, playlist_id: int) -> Dict[str, Any]:
        try:
            success = db.delete_playlist(playlist_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_playlist_items(self, playlist_id: int, wallpaper_ids: List[int]) -> Dict[str, Any]:
        try:
            db.set_playlist_items(playlist_id, wallpaper_ids)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Automations ---
    def get_automations(self) -> Dict[str, Any]:
        try:
            return {"success": True, "data": db.get_automations()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_automation(self, name: str, trigger_type: str, trigger_condition: str, action_type: str, action_target: str, is_enabled: int = 1) -> Dict[str, Any]:
        try:
            aid = db.add_automation(name, trigger_type, trigger_condition, action_type, action_target, is_enabled)
            return {"success": True, "id": aid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def toggle_automation(self, auto_id: int, is_enabled: bool) -> Dict[str, Any]:
        try:
            db.toggle_automation(auto_id, is_enabled)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_automation(self, auto_id: int) -> Dict[str, Any]:
        try:
            success = db.delete_automation(auto_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Moniteurs & Matériel ---
    def get_monitors(self) -> Dict[str, Any]:
        try:
            monitors = monitor_detector.get_monitors(force_refresh=True)
            bounding_box = monitor_detector.get_bounding_box()
            return {"success": True, "data": monitors, "bounding_box": bounding_box}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_power_status(self) -> Dict[str, Any]:
        try:
            return {"success": True, "data": power_monitor.get_status()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Configuration & Diagnostics ---
    def get_config(self) -> Dict[str, Any]:
        return {"success": True, "data": config_manager.get_all()}

    def update_config(self, key: str, value: Any) -> Dict[str, Any]:
        try:
            config_manager.set(key, value)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_performance_profiles(self) -> Dict[str, Any]:
        return {"success": True, "data": PERFORMANCE_PROFILES}

    def set_performance_profile(self, profile_name: str) -> Dict[str, Any]:
        if profile_name in PERFORMANCE_PROFILES or profile_name == "Custom":
            config_manager.set("performance_profile", profile_name)
            return {"success": True}
        return {"success": False, "error": "Profil inconnu"}

    def get_system_info(self) -> Dict[str, Any]:
        try:
            return {"success": True, "data": system_detector.detect_all(force_refresh=True)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_cache_stats(self) -> Dict[str, Any]:
        try:
            return {"success": True, "data": cache_manager.get_cache_stats()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear_cache(self, clear_thumbnails: bool = True, clear_processed: bool = True) -> Dict[str, Any]:
        try:
            res = cache_manager.clear_cache(clear_thumbnails, clear_processed)
            return {"success": True, "data": res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_recent_logs(self, limit: int = 100) -> Dict[str, Any]:
        return {"success": True, "data": get_recent_logs(limit)}

    def get_history(self, limit: int = 50) -> Dict[str, Any]:
        try:
            return {"success": True, "data": db.get_history(limit)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_scheduler_status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "is_running": scheduler.is_running(),
            "time_remaining": scheduler.get_time_remaining(),
            "interval": config_manager.get("auto_change.interval_seconds", 300),
            "mode": config_manager.get("auto_change.mode", "order")
        }

    def toggle_scheduler(self, enable: bool) -> Dict[str, Any]:
        if enable:
            scheduler.start()
        else:
            scheduler.stop()
        config_manager.set("auto_change.enabled", enable)
        return {"success": True, "is_running": scheduler.is_running()}

    def is_autostart_enabled(self) -> Dict[str, Any]:
        return {"success": True, "enabled": autostart_manager.is_enabled()}

    def set_autostart(self, enabled: bool) -> Dict[str, Any]:
        success = autostart_manager.set_enabled(enabled)
        config_manager.set("start_at_login", enabled)
        return {"success": success}

    # Contrôles de la fenêtre
    def minimize_window(self) -> Dict[str, Any]:
        if self.window:
            self.window.minimize()
            return {"success": True}
        return {"success": False}

    def hide_window(self) -> Dict[str, Any]:
        if self.window:
            self.window.hide()
            return {"success": True}
        return {"success": False}

    def show_window(self) -> Dict[str, Any]:
        if self.window:
            self.window.show()
            self.window.restore()
            return {"success": True}
        return {"success": False}
