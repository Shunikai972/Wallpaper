"""Interface abstraite de moteur de fond d'écran pour Linux."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseWallpaperEngine(ABC):
    """Classe de base pour tous les moteurs de fond d'écran."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifiant unique du moteur (ex: gnome, kde, mpvpaper, etc.)."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Nom lisible pour l'interface."""
        pass

    @property
    @abstractmethod
    def supported_types(self) -> List[str]:
        """Types de médias supportés: ['image', 'gif', 'video']."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si les outils requis sont installés et compatibles avec la session courante."""
        pass

    @abstractmethod
    def apply(self, wallpaper_path: str, monitor: str = "all", options: Optional[Dict[str, Any]] = None) -> bool:
        """Applique le fond d'écran sur le ou les moniteurs spécifiés."""
        pass

    def pause(self, monitor: str = "all") -> bool:
        """Met en pause l'animation ou la vidéo (si supporté)."""
        return False

    def resume(self, monitor: str = "all") -> bool:
        """Reprend la lecture de l'animation ou vidéo (si supporté)."""
        return False

    def stop(self, monitor: str = "all") -> bool:
        """Arrête le moteur ou le processus associé."""
        return True

    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état courant d'exécution du moteur."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": self.is_available(),
            "supported_types": self.supported_types,
            "is_running": False
        }
