"""Bus d'événements simple et découplé pour la communication inter-services."""

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any

logger = logging.getLogger("wallpapermaison.events")

class EventBus:
    """Bus d'événements synchrone et thread-safe."""
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        """Enregistre un écouteur pour un événement donné."""
        if callback not in self._listeners[event_name]:
            self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        """Désenregistre un écouteur."""
        if event_name in self._listeners and callback in self._listeners[event_name]:
            self._listeners[event_name].remove(callback)

    def emit(self, event_name: str, **kwargs: Any) -> None:
        """Diffuse un événement à tous ses écouteurs."""
        callbacks = list(self._listeners.get(event_name, []))
        for cb in callbacks:
            try:
                cb(**kwargs)
            except Exception as e:
                logger.error("Erreur lors de l'exécution de l'événement '%s': %s", event_name, e, exc_info=True)

# Instance globale
bus = EventBus()
