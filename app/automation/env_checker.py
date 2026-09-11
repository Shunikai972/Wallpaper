"""Surveillance périodique du fichier .env et téléchargement automatique de wallpaperlink."""

import hashlib
import logging
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("wallpapermaison.env_checker")

DEFAULT_CHECK_INTERVAL = 30  # secondes
MIN_CHECK_INTERVAL = 3  # secondes

class EnvChecker:
    """Surveille le fichier .env et synchronise automatiquement le fond d'écran."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_link: str = ""
        self._last_downloaded_path: str = ""
        self._last_applied_mtime: float = 0.0

    @property
    def downloads_dir(self) -> Path:
        """Dossier de stockage des fonds d'écran téléchargés."""
        p = Path.home() / ".local/share/wallpapermaison/downloads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def find_env_file(self) -> Optional[Path]:
        """Localise le fichier .env actif."""
        candidates = [
            self.project_root / ".env",
            Path.home() / "reseau/Perso/Bureau/Wallpaper/.env",
            Path.home() / "Bureau/Wallpaper/.env",
            Path.home() / "Wallpaper/.env"
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    def read_env_config(self) -> Dict[str, Any]:
        """Lit et extrait les paramètres wallpaperlink et check_interval du .env."""
        env_file = self.find_env_file()
        if not env_file or not env_file.is_file():
            return {"wallpaperlink": "", "check_interval": DEFAULT_CHECK_INTERVAL}

        link = ""
        interval = DEFAULT_CHECK_INTERVAL

        try:
            content = env_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip().lower()
                    val = val.strip().strip("'\"")
                    if key == "wallpaperlink":
                        link = val
                    elif key in ("check_interval", "interval", "checkinterval"):
                        try:
                            parsed_int = int(val)
                            if parsed_int >= MIN_CHECK_INTERVAL:
                                interval = parsed_int
                        except ValueError:
                            pass
        except Exception as e:
            logger.warning("Erreur lecture .env: %s", e)

        return {"wallpaperlink": link, "check_interval": interval}

    def sanitize_filename(self, name: str) -> str:
        """Nettoie le nom de fichier pour éviter les caractères invalides."""
        name = re.sub(r'[\\/*?:\"<>|]', "", name)
        return name.strip() or "wallpaper.mp4"

    def detect_extension(self, file_path: Path, fallback: str = ".mp4") -> str:
        """Détecte l'extension appropriée selon les magic bytes du fichier."""
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)
            if header.startswith(b"\xff\xd8\xff"):
                return ".jpg"
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return ".png"
            if header.startswith((b"GIF87a", b"GIF89a")):
                return ".gif"
            if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
                return ".webp"
            if len(header) >= 8 and (b"ftyp" in header[:16] or header[4:8] == b"ftyp"):
                return ".mp4"
            if header.startswith(b"\x1a\x45\xdf\xa3"):
                return ".webm"
        except Exception:
            pass
        return fallback

    def download_media_if_needed(self, url: str) -> Optional[Path]:
        """Télécharge le fichier média depuis l'URL si nécessaire."""
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https"):
                logger.warning("Protocole non supporté pour wallpaperlink: %s", parsed.scheme)
                return None

            # Détermination de l'extension et du nom de fichier
            url_path = parsed.path
            raw_filename = os.path.basename(url_path)
            clean_name = self.sanitize_filename(raw_filename)

            # Si aucune extension reconnue, on déduit .mp4 par défaut
            ext = os.path.splitext(clean_name)[1].lower()
            if ext not in (".mp4", ".webm", ".mkv", ".png", ".jpg", ".jpeg", ".webp", ".gif"):
                clean_name += ".mp4"

            # Préfixe de hachage court pour éviter les collisions d'URLs avec le même nom
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
            target_filename = f"{url_hash}_{clean_name}"
            target_path = self.downloads_dir / target_filename

            # Vérification si le fichier existe déjà et est valide
            if target_path.exists() and target_path.stat().st_size > 1024:
                logger.debug("Le fichier téléchargé existe déjà : %s", target_path)
                return target_path

            logger.info("Téléchargement du nouveau wallpaper depuis %s -> %s", url, target_path)
            tmp_target = target_path.with_suffix(".tmp")

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "WallpaperMaison/1.0 (Linux; Fedora Silverblue)"}
            )

            with urllib.request.urlopen(req, timeout=30) as response, open(tmp_target, "wb") as out_file:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    out_file.write(chunk)

            if tmp_target.exists() and tmp_target.stat().st_size > 0:
                detected_ext = self.detect_extension(tmp_target, fallback=ext if ext else ".mp4")
                if ext != detected_ext:
                    clean_base = os.path.splitext(clean_name)[0]
                    target_filename = f"{url_hash}_{clean_base}{detected_ext}"
                    target_path = self.downloads_dir / target_filename
                tmp_target.replace(target_path)
                logger.info("Téléchargement réussi : %s (%d octets)", target_path, target_path.stat().st_size)
                return target_path
            else:
                if tmp_target.exists():
                    tmp_target.unlink()
                logger.error("Téléchargement incomplet ou vide pour %s", url)
                return None

        except Exception as e:
            logger.error("Erreur lors du téléchargement de %s: %s", url, e)
            return None

    def check_and_apply(self) -> bool:
        """Exécute une vérification du fichier .env et applique le wallpaper si nécessaire."""
        cfg = self.read_env_config()
        link = cfg.get("wallpaperlink", "").strip()

        if not link:
            return False

        # Cas 1: URL distante
        if link.startswith(("http://", "https://")):
            dest_file = self.download_media_if_needed(link)
            if not dest_file or not dest_file.exists():
                return False
            final_path = str(dest_file)

        # Cas 2: Fichier local
        else:
            p = Path(link).expanduser()
            if not p.is_file():
                logger.warning("Fichier local introuvable spécifié dans wallpaperlink: %s", link)
                return False
            final_path = str(p.resolve())

        # Si le fichier est déjà celui qu'on a appliqué récemment
        if final_path == self._last_downloaded_path and link == self._last_link:
            return False

        try:
            from app.media.scanner import media_scanner
            from app.wallpaper.manager import wallpaper_manager

            imported = media_scanner.import_single_file(final_path)
            if not imported or "id" not in imported:
                logger.error("Impossible d'importer le média %s dans la bibliothèque.", final_path)
                return False

            wp_id = imported["id"]
            current_wp = wallpaper_manager.get_current_wallpaper()
            if current_wp and current_wp.get("id") == wp_id:
                self._last_link = link
                self._last_downloaded_path = final_path
                return False

            logger.info("Application automatique du wallpaper issu de .env: %s (id: %s)", final_path, wp_id)
            success = wallpaper_manager.apply_wallpaper(wp_id)
            if success:
                self._last_link = link
                self._last_downloaded_path = final_path
                return True
            return False

        except Exception as e:
            logger.error("Erreur lors de l'application de %s: %s", final_path, e)
            return False

    def _loop(self) -> None:
        """Boucle d'exécution périodique."""
        logger.info("Boucle de vérification .env démarrée.")
        while not self._stop_event.is_set():
            cfg = self.read_env_config()
            interval = cfg.get("check_interval", DEFAULT_CHECK_INTERVAL)

            try:
                self.check_and_apply()
            except Exception as e:
                logger.error("Erreur boucle env_checker: %s", e)

            for _ in range(int(interval)):
                if self._stop_event.is_set():
                    break
                time.sleep(1.0)

    def start(self) -> None:
        """Démarre le service de surveillance."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="EnvCheckerThread", daemon=True)
        self._thread.start()
        logger.info("EnvChecker démarré avec succès.")

    def stop(self) -> None:
        """Arrête le service de surveillance."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("EnvChecker arrêté.")

env_checker = EnvChecker()
