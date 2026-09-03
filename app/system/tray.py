"""Gestionnaire d'icône dans la barre des tâches (System Tray) avec menu rapide."""

import logging
import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw

logger = logging.getLogger("wallpapermaison.tray")

class SystemTrayManager:
    """Gère l'icône dans la zone de notification Linux."""
    def __init__(self,
                 on_open: Optional[Callable[[], None]] = None,
                 on_next: Optional[Callable[[], None]] = None,
                 on_prev: Optional[Callable[[], None]] = None,
                 on_pause: Optional[Callable[[], None]] = None,
                 on_resume: Optional[Callable[[], None]] = None,
                 on_favorite: Optional[Callable[[], None]] = None,
                 on_set_profile: Optional[Callable[[str], None]] = None,
                 on_quit: Optional[Callable[[], None]] = None) -> None:
        self.on_open = on_open
        self.on_next = on_next
        self.on_prev = on_prev
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_favorite = on_favorite
        self.on_set_profile = on_set_profile
        self.on_quit = on_quit

        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self.is_available = False

        self._init_tray()

    def _init_tray(self) -> None:
        """Détecte la disponibilité du System Tray selon l'environnement Linux."""
        try:
            import os
            # 1. Vérifier si AppIndicator3 ou AyatanaAppIndicator3 est disponible via GObject
            has_appindicator = False
            try:
                import gi
                gi.require_version("AppIndicator3", "0.1")
                from gi.repository import AppIndicator3  # noqa: F401
                has_appindicator = True
            except Exception:
                try:
                    import gi
                    gi.require_version("AyatanaAppIndicator3", "0.1")
                    from gi.repository import AyatanaAppIndicator3  # noqa: F401
                    has_appindicator = True
                except Exception:
                    has_appindicator = False

            # 2. Si pas d'AppIndicator, tester si un Tray Manager X11 écoute
            if not has_appindicator:
                os.environ.setdefault("PYSTRAY_BACKEND", "xorg")
                try:
                    from Xlib import display
                    d = display.Display()
                    tray_atom = d.intern_atom(f"_NET_SYSTEM_TRAY_S{d.get_default_screen()}")
                    owner = d.get_selection_owner(tray_atom)
                    d.close()
                    if not owner:
                        logger.info("Aucun gestionnaire de barre des tâches (System Tray) actif sous cette session. Mode fenêtre standard activé.")
                        self.is_available = False
                        return
                except Exception:
                    self.is_available = False
                    return

            import pystray
            self.is_available = True
        except Exception as e:
            logger.info("System Tray non disponible (%s). L'icône de tray sera désactivée.", e)
            self.is_available = False

    def _create_tray_icon_image(self) -> Image.Image:
        """Génère une icône minimaliste moderne 64x64."""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Cercle extérieur émeraude / ambre
        draw.ellipse((4, 4, 60, 60), fill=(24, 28, 37, 255), outline=(163, 190, 140, 255), width=4)
        # Forme stylisée de montagne / wallpaper
        draw.polygon([(16, 44), (28, 24), (38, 38), (48, 20), (52, 44)], fill=(163, 190, 140, 255))
        return img

    def start(self) -> None:
        """Démarre le system tray dans un thread séparé."""
        if not self.is_available:
            return

        try:
            import pystray
            from pystray import MenuItem as item

            menu = pystray.Menu(
                item("Ouvrir WallpaperMaison", lambda: self.on_open() if self.on_open else None, default=True),
                pystray.Menu.SEPARATOR,
                item("Fond suivant ⏭", lambda: self.on_next() if self.on_next else None),
                item("Fond précédent ⏮", lambda: self.on_prev() if self.on_prev else None),
                item("Mettre en pause ⏸", lambda: self.on_pause() if self.on_pause else None),
                item("Reprendre ▶", lambda: self.on_resume() if self.on_resume else None),
                item("Ajouter aux favoris ⭐", lambda: self.on_favorite() if self.on_favorite else None),
                pystray.Menu.SEPARATOR,
                item("Mode Performance", pystray.Menu(
                    item("Quality (60 FPS)", lambda: self.on_set_profile("Quality") if self.on_set_profile else None),
                    item("Balanced (30 FPS)", lambda: self.on_set_profile("Balanced") if self.on_set_profile else None),
                    item("Performance (24 FPS)", lambda: self.on_set_profile("Performance") if self.on_set_profile else None),
                    item("Battery Saver (Statique)", lambda: self.on_set_profile("Battery Saver") if self.on_set_profile else None)
                )),
                pystray.Menu.SEPARATOR,
                item("Quitter", lambda: self.stop() or (self.on_quit() if self.on_quit else None))
            )

            icon_image = self._create_tray_icon_image()
            self._icon = pystray.Icon("wallpapermaison", icon_image, "WallpaperMaison", menu)

            self._thread = threading.Thread(target=self._icon.run, daemon=True, name="SystemTrayThread")
            self._thread.start()
            logger.info("System Tray démarré avec succès.")
        except Exception as e:
            logger.warning("Impossible d'initialiser le System Tray: %s", e)

    def stop(self) -> None:
        """Arrête l'icône de tray."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
