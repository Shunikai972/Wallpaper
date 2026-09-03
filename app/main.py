"""Point d'entrée principal de l'application WallpaperMaison."""

import argparse
import logging
import os
import signal
import sys
import threading
from pathlib import Path

# Prise en charge du mode compilé PyInstaller (sys._MEIPASS) ou exécution normale
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ROOT_DIR = Path(sys._MEIPASS)
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import __version__, __app_name__
from app.api.bridge import AppBridge
from app.automation.rules import rule_engine
from app.automation.scheduler import scheduler
from app.core.config import config_manager, LOGS_DIR
from app.core.logger import setup_logger
from app.storage.database import db
from app.system.power import power_monitor
from app.system.tray import SystemTrayManager
from app.system.window_monitor import window_monitor
from app.wallpaper.manager import wallpaper_manager

logger = setup_logger(LOGS_DIR)

class Application:
    """Gestionnaire du cycle de vie de l'application."""

    def __init__(self, start_minimized: bool = False, daemon_mode: bool = False) -> None:
        self.start_minimized = start_minimized or config_manager.get("start_minimized", False)
        self.daemon_mode = daemon_mode
        self.bridge = AppBridge()
        self.window = None
        self.tray = None
        self._shutdown_event = threading.Event()

    def setup_services(self) -> None:
        """Démarre les services d'arrière-plan."""
        logger.info("Démarrage des services d'arrière-plan...")
        power_monitor.start()
        window_monitor.start()
        rule_engine.start()

        if config_manager.get("auto_change.enabled", False):
            scheduler.start()

        # Démarrage de l'icône dans la zone de notification
        self.tray = SystemTrayManager(
            on_open=self._on_tray_open,
            on_next=scheduler.next_wallpaper,
            on_prev=scheduler.previous_wallpaper,
            on_pause=wallpaper_manager.pause,
            on_resume=wallpaper_manager.resume,
            on_favorite=self._on_tray_favorite,
            on_set_profile=lambda p: config_manager.set("performance_profile", p),
            on_quit=self.shutdown
        )
        self.tray.start()

    def _on_tray_open(self) -> None:
        if self.window:
            self.window.show()
            self.window.restore()

    def _on_tray_favorite(self) -> None:
        cur = wallpaper_manager.get_current_wallpaper()
        if cur and "id" in cur:
            db.toggle_favorite(cur["id"])

    def on_closing(self) -> bool:
        """Intercepte la fermeture de la fenêtre pour minimiser dans le tray si configuré."""
        if config_manager.get("minimize_to_tray", True) and self.tray and self.tray.is_available:
            logger.info("Minimisation dans la zone de notification.")
            if self.window:
                self.window.hide()
            return False # Annule la fermeture complète
        self.shutdown()
        return True

    def run(self) -> None:
        """Lance l'interface utilisateur PyWebView."""
        self.setup_services()

        html_file = ROOT_DIR / "ui" / "index.html"
        if not html_file.exists():
            logger.critical("Fichier d'interface introuvable: %s", html_file)
            sys.exit(1)

        try:
            import webview
        except ImportError:
            logger.critical("Le module 'pywebview' n'est pas installé. Exécutez: pip install pywebview")
            sys.exit(1)

        logger.info("Création de la fenêtre PyWebView...")
        self.window = webview.create_window(
            title=f"{__app_name__} v{__version__} - Linux Fedora Wallpaper Engine",
            url=str(html_file.resolve().as_uri()),
            width=1280,
            height=820,
            min_size=(980, 620),
            background_color="#0B0E14",
            js_api=self.bridge,
            text_select=False
        )
        self.bridge.set_window(self.window)
        self.window.events.closing += self.on_closing

        # Gestion des signaux d'arrêt propres (SIGINT, SIGTERM)
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())

        if self.daemon_mode:
            logger.info("Mode démon actif, en attente...")
            self._shutdown_event.wait()
            self.shutdown()
        else:
            # Lancement de la boucle PyWebView
            # Sur Linux, webkit2gtk est utilisé par défaut
            webview.start(debug=False)
            self.shutdown()

    def shutdown(self) -> None:
        """Arrête proprement l'ensemble des threads et processus enfants."""
        logger.info("Fermeture propre de WallpaperMaison...")
        self._shutdown_event.set()

        try:
            scheduler.stop()
            rule_engine.stop()
            power_monitor.stop()
            window_monitor.stop()
            if self.tray:
                self.tray.stop()
            # Note: Le fond d'écran actif reste appliqué sur le bureau Linux
        except Exception as e:
            logger.error("Erreur lors de l'arrêt des services: %s", e)

        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        sys.exit(0)

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{__app_name__} - Gestionnaire moderne de fonds d'écran sous Linux Fedora")
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    parser.add_argument("--minimized", action="store_true", help="Démarrer l'application minimisée dans la barre des tâches")
    parser.add_argument("--daemon", action="store_true", help="Lancer en mode démon sans interface graphique")
    parser.add_argument("--scan", type=str, help="Scanne un dossier spécifique et quitte")
    args = parser.parse_args()

    if args.scan:
        logger.info("Scan unique demandé pour: %s", args.scan)
        from app.media.scanner import media_scanner
        media_scanner.scan_directories_async([args.scan], recursive=True)
        return

    app = Application(start_minimized=args.minimized, daemon_mode=args.daemon)
    app.run()

if __name__ == "__main__":
    main()
