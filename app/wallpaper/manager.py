"""Gestionnaire central et orchestrateur des moteurs de fond d'écran."""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import config_manager
from app.core.events import bus
from app.image_processing.adjuster import image_adjuster
from app.storage.database import db
from app.system.detector import system_detector
from app.system.monitors import monitor_detector
from app.wallpaper.base import BaseWallpaperEngine
from app.wallpaper.engines.gnome_engine import GnomeWallpaperEngine
from app.wallpaper.engines.kde_engine import KdeWallpaperEngine
from app.wallpaper.engines.mpvpaper_engine import MpvpaperWallpaperEngine
from app.wallpaper.engines.swww_engine import SwwwWallpaperEngine
from app.wallpaper.engines.xwinwrap_engine import XwinwrapWallpaperEngine
from app.wallpaper.engines.feh_engine import FehWallpaperEngine
from app.wallpaper.engines.gtk_video_engine import GtkVideoWallpaperEngine
from app.wallpaper.engines.hanabi_engine import HanabiWallpaperEngine
from app.wallpaper.engines.fallback_engine import FallbackWallpaperEngine

logger = logging.getLogger("wallpapermaison.wallpaper_manager")

class WallpaperManager:
    """Orchestrateur central des fonds d'écran."""

    def __init__(self) -> None:
        self.engines: Dict[str, BaseWallpaperEngine] = {
            "gnome": GnomeWallpaperEngine(),
            "kde": KdeWallpaperEngine(),
            "hanabi": HanabiWallpaperEngine(),
            "mpvpaper": MpvpaperWallpaperEngine(),
            "gtk_video": GtkVideoWallpaperEngine(),
            "swww": SwwwWallpaperEngine(),
            "xwinwrap": XwinwrapWallpaperEngine(),
            "feh": FehWallpaperEngine(),
            "fallback": FallbackWallpaperEngine()
        }
        self._current_wallpapers: Dict[str, Dict[str, Any]] = {} # monitor -> wallpaper dict
        self._active_engine_name: Optional[str] = None
        self._is_paused = False

        # Abonnements aux événements système
        bus.subscribe("fullscreen_state_changed", self._on_fullscreen_changed)
        bus.subscribe("power_changed", self._on_power_changed)
        bus.subscribe("screen_locked", self._on_screen_locked)

    def select_engine_for(self, media_type: str) -> BaseWallpaperEngine:
        """Sélectionne dynamiquement le moteur le plus pertinent selon le média et la configuration."""
        pref = config_manager.get("preferred_engine", "auto")
        if pref != "auto" and pref in self.engines and self.engines[pref].is_available():
            if media_type in self.engines[pref].supported_types:
                return self.engines[pref]

        sys_info = system_detector.detect_all()
        session = sys_info.get("session_type", "wayland")
        de = sys_info.get("desktop_env", "gnome")
        tools = sys_info.get("tools", {})

        # Cas 1: Vidéo
        if media_type == "video":
            # 1. Priorité absolue : Extension GNOME Shell native (vidéo directement dans le compositeur Mutter)
            if self.engines["hanabi"].is_available():
                return self.engines["hanabi"]
            if session == "wayland" and tools.get("mpvpaper", {}).get("installed"):
                return self.engines["mpvpaper"]
            elif session == "x11" and tools.get("xwinwrap", {}).get("installed"):
                return self.engines["xwinwrap"]
            # Moteur vidéo autonome accéléré (fenêtre de fond d'écran MPV)
            if self.engines["gtk_video"].is_available():
                return self.engines["gtk_video"]
            # Si pas de moteur vidéo externe, tenter mpvpaper ou fallback
            if self.engines["mpvpaper"].is_available():
                return self.engines["mpvpaper"]
            return self.engines["fallback"]

        # Cas 2: GIF animé
        elif media_type == "gif":
            if session == "wayland":
                if tools.get("swww", {}).get("installed"):
                    return self.engines["swww"]
                if tools.get("mpvpaper", {}).get("installed"):
                    return self.engines["mpvpaper"]
            elif session == "x11" and tools.get("xwinwrap", {}).get("installed"):
                return self.engines["xwinwrap"]
            if de == "gnome" and self.engines["gnome"].is_available():
                return self.engines["gnome"]
            return self.engines["fallback"]

        # Cas 3: Image statique
        else:
            if de == "gnome" and self.engines["gnome"].is_available():
                return self.engines["gnome"]
            if de == "kde" and self.engines["kde"].is_available():
                return self.engines["kde"]
            if session == "wayland" and self.engines["swww"].is_available():
                return self.engines["swww"]
            if session == "x11" and self.engines["feh"].is_available():
                return self.engines["feh"]

        # Si aucun moteur natif ne correspond
        for eng in self.engines.values():
            if eng.is_available() and media_type in eng.supported_types:
                return eng

        return self.engines["fallback"]

    def apply_wallpaper(self, wallpaper_id: int, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        """Applique un wallpaper depuis la base de données."""
        wp = db.get_wallpaper_by_id(wallpaper_id)
        if not wp:
            logger.error("Wallpaper id=%s introuvable dans la base.", wallpaper_id)
            return False

        file_path = Path(wp["file_path"])
        if not file_path.exists():
            logger.error("Fichier source introuvable: %s", file_path)
            return False

        media_type = wp.get("media_type", "image")

        # Vérification si des ajustements d'image existent
        effective_path = str(file_path)
        if media_type == "image":
            adj = db.get_adjustments(wallpaper_id)
            if adj:
                effective_path = image_adjuster.apply_adjustments(file_path, adj)

        # Paramètres de performance actifs
        profile = config_manager.get_active_profile_settings()
        merged_opts = {**profile, **(options or {})}

        engine = self.select_engine_for(media_type)

        # Arrêt du moteur précédent s'il était actif ou en cas de changement
        if self._active_engine_name and self._active_engine_name in self.engines:
            if self._active_engine_name != engine.name or engine.name == "gtk_video":
                self.engines[self._active_engine_name].stop(monitor)

        self._active_engine_name = engine.name
        logger.info("Application du wallpaper '%s' (id: %s) via le moteur '%s' sur l'écran '%s'",
                    wp["file_name"], wallpaper_id, engine.name, monitor)

        success = engine.apply(effective_path, monitor=monitor, options=merged_opts)
        if success:
            self._current_wallpapers[monitor] = wp
            self._is_paused = False
            db.record_applied(wallpaper_id, monitor=monitor)
            if media_type == "video":
                self._sync_vscode(effective_path)
            bus.emit("wallpaper_changed", wallpaper=wp, monitor=monitor, engine=engine.name)
            return True
        else:
            logger.warning("Échec de l'application via %s, tentative avec le moteur de secours.", engine.name)
            self.engines["fallback"].apply(effective_path, monitor=monitor, options=merged_opts)
            self._current_wallpapers[monitor] = wp
            return False

    def pause(self, monitor: str = "all") -> bool:
        """Met en pause le moteur actif."""
        if self._active_engine_name and self._active_engine_name in self.engines:
            res = self.engines[self._active_engine_name].pause(monitor)
            self._is_paused = True
            bus.emit("wallpaper_paused", monitor=monitor)
            return res
        return False

    def resume(self, monitor: str = "all") -> bool:
        """Reprend le moteur actif."""
        if self._active_engine_name and self._active_engine_name in self.engines:
            res = self.engines[self._active_engine_name].resume(monitor)
            self._is_paused = False
            bus.emit("wallpaper_resumed", monitor=monitor)
            return res
        return False

    def get_current_wallpaper(self, monitor: str = "all") -> Optional[Dict[str, Any]]:
        """Retourne les informations du fond d'écran actuellement actif."""
        if monitor in self._current_wallpapers:
            return self._current_wallpapers[monitor]
        if "all" in self._current_wallpapers:
            return self._current_wallpapers["all"]
        # Récupération depuis le dernier historique
        hist = db.get_history(limit=1)
        return hist[0] if hist else None

    def restore_last_wallpaper(self) -> bool:
        """Restaure et applique automatiquement le dernier fond d'écran actif."""
        try:
            # 1. Vérifier si current_wallpaper.json contient un fond d'écran actif valide
            state_file = Path.home() / ".config/wallpapermaison/current_wallpaper.json"
            if state_file.exists():
                try:
                    import json
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    p = data.get("path")
                    if p and os.path.exists(p):
                        logger.info("Restauration automatique depuis current_wallpaper.json: %s", p)
                        return self.apply_wallpaper_by_path(p)
                except Exception:
                    pass

            # 2. Vérifier l'historique en base de données
            hist = db.get_history(limit=1)
            if hist and len(hist) > 0:
                wp_id = hist[0].get("id") or hist[0].get("wallpaper_id")
                if wp_id:
                    logger.info("Restauration automatique du fond d'écran précédent (ID: %s)", wp_id)
                    return self.apply_wallpaper(wp_id)

            wps = db.get_wallpapers(limit=1)
            if wps and len(wps) > 0:
                wp_id = wps[0]["id"]
                logger.info("Application du premier fond d'écran disponible (ID: %s)", wp_id)
                return self.apply_wallpaper(wp_id)
        except Exception as e:
            logger.error("Erreur lors de la restauration du fond d'écran: %s", e)
        return False

    def apply_wallpaper_by_path(self, file_path: str, monitor: str = "all") -> bool:
        """Importe et applique directement un fond d'écran à partir de son chemin de fichier."""
        p = Path(file_path).expanduser().resolve()
        if not p.exists():
            logger.error("Fichier introuvable pour application directe: %s", file_path)
            return False
        from app.media.scanner import media_scanner
        imported = media_scanner.import_single_file(str(p))
        if imported and "id" in imported:
            return self.apply_wallpaper(imported["id"], monitor=monitor)
        return False

    def _sync_vscode(self, video_path: str) -> None:
        """Synchronise automatiquement le live wallpaper avec Visual Studio Code."""
        try:
            from app.automation.vscode_sync import vscode_sync
            vscode_sync.publish_state(video_path, media_type="video", source="desktop")
        except Exception as e:
            logger.debug("Erreur synchronisation VS Code via vscode_sync: %s", e)

    def get_engines_status(self) -> List[Dict[str, Any]]:
        """Retourne la liste des moteurs et leur statut pour les paramètres."""
        return [eng.get_status() for eng in self.engines.values()]

    # Événements système réactifs
    def _on_fullscreen_changed(self, is_fullscreen: bool) -> None:
        profile = config_manager.get_active_profile_settings()
        if profile.get("pause_on_fullscreen"):
            if is_fullscreen:
                logger.info("Application plein écran active -> Pause automatique du fond d'écran.")
                self.pause()
            else:
                logger.info("Fin du plein écran -> Reprise de la vidéo.")
                self.resume()

    def _on_power_changed(self, on_battery: bool, percentage: float) -> None:
        profile = config_manager.get_active_profile_settings()
        if on_battery and profile.get("pause_on_battery"):
            logger.info("Passage sur batterie -> Pause du fond animé pour préserver l'autonomie.")
            self.pause()
        elif not on_battery:
            logger.info("Alimentation secteur connectée -> Reprise de l'animation.")
            self.resume()

    def _on_screen_locked(self, is_locked: bool) -> None:
        profile = config_manager.get_active_profile_settings()
        if profile.get("pause_on_lock"):
            if is_locked:
                self.pause()
            else:
                self.resume()

wallpaper_manager = WallpaperManager()
