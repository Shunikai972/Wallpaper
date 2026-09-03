"""Système de journalisation structuré avec buffer circulaire pour l'UI."""

import logging
import os
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Dict, Any

# Buffer en mémoire pour la console de diagnostics de l'interface
_LOG_BUFFER: deque = deque(maxlen=200)

class UILogHandler(logging.Handler):
    """Handler qui stocke les derniers logs pour l'interface utilisateur."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            _LOG_BUFFER.append({
                "timestamp": record.created,
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
                "formatted": msg
            })
        except Exception:
            self.handleError(record)

def setup_logger(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure et retourne le logger racine de l'application."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "wallpapermaison.log"

    logger = logging.getLogger("wallpapermaison")
    logger.setLevel(level)

    # Évite les doublons de handlers si appelé plusieurs fois
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Fichier rotatif (max 5 MB x 3 fichiers)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler mémoire UI
    ui_handler = UILogHandler()
    ui_handler.setFormatter(formatter)
    logger.addHandler(ui_handler)

    logger.info("Système de journalisation initialisé. Fichier log: %s", log_file)
    return logger

def get_recent_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retourne les logs récents pour la page de diagnostic."""
    items = list(_LOG_BUFFER)
    return items[-limit:]
