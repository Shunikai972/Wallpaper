"""Gestionnaire de configuration et de profils de performance."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("wallpapermaison.config")

# Chemins standards XDG et détection de persistance réseau (IUT NFS reseau/Perso)
HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PERSISTENT_ROOT: Optional[Path] = None
network_perso = HOME / "reseau" / "Perso"
marker_file = REPO_ROOT / ".persistent_mode"

if os.environ.get("WALLPAPERMAISON_PERSISTENT") == "1" or marker_file.exists():
    if network_perso.exists():
        PERSISTENT_ROOT = network_perso
elif network_perso.exists() and (network_perso / ".config" / "wallpapermaison").exists():
    PERSISTENT_ROOT = network_perso

if PERSISTENT_ROOT and PERSISTENT_ROOT.exists():
    CONFIG_DIR = PERSISTENT_ROOT / ".config" / "wallpapermaison"
    DATA_DIR = PERSISTENT_ROOT / ".local" / "share" / "wallpapermaison"
    CACHE_DIR = PERSISTENT_ROOT / ".cache" / "wallpapermaison"
    logger.info("Mode de stockage persistant réseau actif : %s", PERSISTENT_ROOT)
else:
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "wallpapermaison"
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share")) / "wallpapermaison"
    CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "wallpapermaison"

THUMBNAIL_DIR = CACHE_DIR / "thumbnails"
PROCESSED_DIR = CACHE_DIR / "processed"
LOGS_DIR = CACHE_DIR / "logs"
CONFIG_FILE = CONFIG_DIR / "config.json"

PERFORMANCE_PROFILES: Dict[str, Dict[str, Any]] = {
    "Quality": {
        "max_fps": 60,
        "max_resolution": "native",
        "hw_decoding": True,
        "pause_on_fullscreen": False,
        "pause_on_battery": False,
        "pause_on_lock": True,
        "ui_animations": True,
        "ui_blur": True
    },
    "Balanced": {
        "max_fps": 30,
        "max_resolution": "1440p",
        "hw_decoding": True,
        "pause_on_fullscreen": True,
        "pause_on_battery": True,
        "pause_on_lock": True,
        "ui_animations": True,
        "ui_blur": True
    },
    "Performance": {
        "max_fps": 24,
        "max_resolution": "1080p",
        "hw_decoding": True,
        "pause_on_fullscreen": True,
        "pause_on_battery": True,
        "pause_on_lock": True,
        "ui_animations": False,
        "ui_blur": False
    },
    "Battery Saver": {
        "max_fps": 15,
        "max_resolution": "1080p",
        "hw_decoding": True,
        "pause_on_fullscreen": True,
        "pause_on_battery": True,
        "force_static_on_battery": True,
        "pause_on_lock": True,
        "ui_animations": False,
        "ui_blur": False
    }
}

def _get_default_library_folders() -> list:
    folders = []
    if PERSISTENT_ROOT and PERSISTENT_ROOT.exists():
        p_wallpapers = PERSISTENT_ROOT / "Images" / "Wallpapers"
        p_test = PERSISTENT_ROOT / "Téléchargements" / "test"
        folders.append(str(p_wallpapers))
        if p_test.exists():
            folders.append(str(p_test))
    folders.append(str(HOME / "Pictures" / "Wallpapers"))
    folders.append(str(HOME / "Pictures"))
    seen = set()
    result = []
    for f in folders:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "onboarding_completed": False,
    "theme": "dark",
    "ui_animations": True,
    "ui_blur": True,
    "start_at_login": False,
    "minimize_to_tray": True,
    "start_minimized": False,
    "performance_profile": "Balanced",
    "library_folders": _get_default_library_folders(),
    "cache_max_size_mb": 2048,  # 2 GB
    "preferred_engine": "auto", # auto, gnome, kde, mpvpaper, swww, feh, xwinwrap
    "auto_change": {
        "enabled": False,
        "interval_seconds": 300, # 5 minutes par défaut
        "mode": "order",         # order, random, random_no_repeat, favorites, tags, folder
        "target_playlist_id": None,
        "target_tags": [],
        "target_folder": None
    },
    "multi_monitor": {
        "mode": "clone",         # clone, individual, span
        "monitors": {}           # monitor_id -> wallpaper_id ou config
    },
    "custom_performance": PERFORMANCE_PROFILES["Balanced"].copy()
}

class ConfigManager:
    """Gestionnaire de persistance et de consultation de la configuration."""
    def __init__(self) -> None:
        self.config_dir = CONFIG_DIR
        self.cache_dir = CACHE_DIR
        self.data_dir = DATA_DIR
        self.config_file = CONFIG_FILE
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.ensure_directories()
        self.load()

    def ensure_directories(self) -> None:
        """Crée tous les dossiers nécessaires s'ils n'existent pas."""
        for d in [self.config_dir, self.cache_dir, self.data_dir, THUMBNAIL_DIR, PROCESSED_DIR, LOGS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def load(self) -> None:
        """Charge la configuration depuis le fichier JSON."""
        if not self.config_file.exists():
            self.save()
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Fusion récursive simple avec les valeurs par défaut
                self._merge_dicts(self._config, saved)
                logger.info("Configuration chargée avec succès depuis %s", self.config_file)
        except Exception as e:
            logger.error("Erreur lors de la lecture de la configuration (%s), chargement des défauts: %s", self.config_file, e)
            self._config = DEFAULT_CONFIG.copy()

    def _merge_dicts(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        for k, v in override.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._merge_dicts(base[k], v)
            else:
                base[k] = v

    def save(self) -> None:
        """Sauvegarde la configuration dans le fichier JSON."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info("Configuration enregistrée dans %s", self.config_file)
        except Exception as e:
            logger.error("Impossible de sauvegarder la configuration: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration (supporte la notation pointée 'a.b.c')."""
        keys = key.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Définit une valeur de configuration (supporte la notation pointée)."""
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        if auto_save:
            self.save()

    def get_all(self) -> Dict[str, Any]:
        """Retourne l'intégralité de la configuration."""
        return self._config.copy()

    def get_active_profile_settings(self) -> Dict[str, Any]:
        """Retourne les paramètres du profil de performance actif."""
        profile_name = self.get("performance_profile", "Balanced")
        if profile_name == "Custom":
            return self.get("custom_performance", PERFORMANCE_PROFILES["Balanced"]).copy()
        return PERFORMANCE_PROFILES.get(profile_name, PERFORMANCE_PROFILES["Balanced"]).copy()

config_manager = ConfigManager()
