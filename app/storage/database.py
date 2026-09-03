"""Base de données SQLite avec migrations automatiques et gestion robuste."""

import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import DATA_DIR

logger = logging.getLogger("wallpapermaison.database")

DB_PATH = DATA_DIR / "wallpapermaison.db"

# Définition des migrations par version
MIGRATIONS = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS wallpapers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_hash TEXT,
            media_type TEXT NOT NULL, -- 'image', 'gif', 'video'
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            duration REAL DEFAULT 0.0,
            fps REAL DEFAULT 0.0,
            thumbnail_path TEXT,
            is_favorite INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            view_count INTEGER DEFAULT 0,
            last_applied TEXT,
            created_at TEXT NOT NULL,
            has_adjustments INTEGER DEFAULT 0
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_wallpapers_favorite ON wallpapers(is_favorite);
        CREATE INDEX IF NOT EXISTS idx_wallpapers_media_type ON wallpapers(media_type);
        CREATE INDEX IF NOT EXISTS idx_wallpapers_last_applied ON wallpapers(last_applied);
        """,
        """
        CREATE TABLE IF NOT EXISTS adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallpaper_id INTEGER UNIQUE NOT NULL,
            brightness REAL DEFAULT 1.0,
            contrast REAL DEFAULT 1.0,
            saturation REAL DEFAULT 1.0,
            vibrance REAL DEFAULT 1.0,
            gamma REAL DEFAULT 1.0,
            exposure REAL DEFAULT 0.0,
            temperature REAL DEFAULT 0.0,
            tint REAL DEFAULT 0.0,
            sharpness REAL DEFAULT 0.0,
            blur REAL DEFAULT 0.0,
            grain REAL DEFAULT 0.0,
            vignette REAL DEFAULT 0.0,
            black_and_white INTEGER DEFAULT 0,
            sepia INTEGER DEFAULT 0,
            crop_x REAL DEFAULT 0.0,
            crop_y REAL DEFAULT 0.0,
            crop_w REAL DEFAULT 1.0,
            crop_h REAL DEFAULT 1.0,
            rotate INTEGER DEFAULT 0,
            flip_h INTEGER DEFAULT 0,
            flip_v INTEGER DEFAULT 0,
            zoom REAL DEFAULT 1.0,
            cached_output_path TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (wallpaper_id) REFERENCES wallpapers(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            icon TEXT DEFAULT 'folder',
            interval_seconds INTEGER DEFAULT 300,
            is_random INTEGER DEFAULT 0,
            target_monitor TEXT DEFAULT 'all',
            schedule_time TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS playlist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            wallpaper_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (wallpaper_id) REFERENCES wallpapers(id) ON DELETE CASCADE,
            UNIQUE(playlist_id, wallpaper_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallpaper_id INTEGER NOT NULL,
            monitor TEXT DEFAULT 'all',
            applied_at TEXT NOT NULL,
            FOREIGN KEY (wallpaper_id) REFERENCES wallpapers(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trigger_type TEXT NOT NULL, -- 'time', 'battery', 'ac_power', 'fullscreen'
            trigger_condition TEXT NOT NULL, -- '08:00', 'on_battery', 'on_ac', 'game_launched'
            action_type TEXT NOT NULL, -- 'set_playlist', 'set_wallpaper', 'pause_video', 'resume_video', 'set_profile'
            action_target TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1
        );
        """
    ]
}

class Database:
    """Gestionnaire de base de données thread-safe avec pool de connexion local."""
    _local = threading.local()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.migrate()
        self._seed_default_data()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conns"):
            self._local.conns = {}
        path_key = str(self.db_path)
        if path_key not in self._local.conns:
            conn = sqlite3.connect(
                path_key,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            self._local.conns[path_key] = conn
        return self._local.conns[path_key]

    def close(self) -> None:
        """Ferme la connexion active pour cette base de données."""
        if hasattr(self._local, "conns"):
            path_key = str(self.db_path)
            conn = self._local.conns.pop(path_key, None)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def migrate(self) -> None:
        """Applique les migrations en attente."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    );
                """)
                cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
                applied = {row[0] for row in cursor.fetchall()}

                for version, queries in sorted(MIGRATIONS.items()):
                    if version not in applied:
                        logger.info("Application de la migration de base de données v%s...", version)
                        for q in queries:
                            conn.executescript(q)
                        conn.execute(
                            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                            (version, datetime.now().isoformat())
                        )
                        logger.info("Migration v%s appliquée avec succès.", version)

    def _seed_default_data(self) -> None:
        """Crée les playlists par défaut et règles si la base est neuve."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM playlists")
        if cursor.fetchone()[0] == 0:
            defaults = [
                ("Nature", "Fonds d'écran naturels et paysages", "tree", 300, 0),
                ("Anime", "Fonds d'écran d'animations et illustrations", "palette", 300, 0),
                ("Dark / Minimal", "Styles sombres épurés et géométriques", "moon", 600, 1),
                ("Gaming", "Jeux vidéo et univers futuristes", "gamepad", 300, 0),
                ("Night", "Ambiance nocturne et repos des yeux", "stars", 900, 0)
            ]
            now = datetime.now().isoformat()
            with conn:
                for name, desc, icon, interval, rand in defaults:
                    conn.execute(
                        "INSERT INTO playlists (name, description, icon, interval_seconds, is_random, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, desc, icon, interval, rand, now)
                    )

        # Automations par défaut
        cursor = conn.execute("SELECT COUNT(*) FROM automations")
        if cursor.fetchone()[0] == 0:
            auto_rules = [
                ("Matin 08:00", "time", "08:00", "set_playlist", "Nature", 0),
                ("Soir 22:00", "time", "22:00", "set_playlist", "Night", 0),
                ("Économie Batterie", "battery", "on_battery", "set_profile", "Battery Saver", 1),
                ("Branché sur Secteur", "ac_power", "on_ac", "set_profile", "Quality", 1),
                ("Jeux / Plein écran", "fullscreen", "game_launched", "pause_video", "all", 1)
            ]
            with conn:
                for name, t_type, t_cond, a_type, a_target, enabled in auto_rules:
                    conn.execute(
                        "INSERT INTO automations (name, trigger_type, trigger_condition, action_type, action_target, is_enabled) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, t_type, t_cond, a_type, a_target, enabled)
                    )

    # --- Wallpapers CRUD ---
    def add_or_update_wallpaper(self, data: Dict[str, Any]) -> int:
        """Insère ou met à jour les informations d'un wallpaper."""
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("SELECT id FROM wallpapers WHERE file_path = ?", (data["file_path"],))
            existing = cursor.fetchone()
            now = datetime.now().isoformat()
            if existing:
                wid = existing[0]
                conn.execute("""
                    UPDATE wallpapers SET
                        file_name = ?, file_size = ?, file_hash = ?, media_type = ?,
                        width = ?, height = ?, duration = ?, fps = ?, thumbnail_path = ?
                    WHERE id = ?
                """, (
                    data.get("file_name", ""),
                    data.get("file_size", 0),
                    data.get("file_hash", ""),
                    data.get("media_type", "image"),
                    data.get("width", 0),
                    data.get("height", 0),
                    data.get("duration", 0.0),
                    data.get("fps", 0.0),
                    data.get("thumbnail_path", ""),
                    wid
                ))
                return wid
            else:
                cur = conn.execute("""
                    INSERT INTO wallpapers (
                        file_path, file_name, file_size, file_hash, media_type,
                        width, height, duration, fps, thumbnail_path, is_favorite,
                        tags, view_count, created_at, has_adjustments
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["file_path"],
                    data.get("file_name", Path(data["file_path"]).name),
                    data.get("file_size", 0),
                    data.get("file_hash", ""),
                    data.get("media_type", "image"),
                    data.get("width", 0),
                    data.get("height", 0),
                    data.get("duration", 0.0),
                    data.get("fps", 0.0),
                    data.get("thumbnail_path", ""),
                    data.get("is_favorite", 0),
                    data.get("tags", ""),
                    0,
                    now,
                    0
                ))
                return cur.lastrowid

    def get_wallpapers(self, search: str = "", media_type: str = "all", favorite_only: bool = False,
                       tag: str = "", sort_by: str = "created_desc", limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
        """Récupère la liste des wallpapers selon des critères de filtre et de tri."""
        conn = self._get_connection()
        query = "SELECT * FROM wallpapers WHERE 1=1"
        params: List[Any] = []

        if search.strip():
            query += " AND (file_name LIKE ? OR tags LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        if media_type and media_type != "all":
            query += " AND media_type = ?"
            params.append(media_type)

        if favorite_only:
            query += " AND is_favorite = 1"

        if tag.strip():
            query += " AND tags LIKE ?"
            params.append(f"%{tag.strip()}%")

        # Tris disponibles
        sort_clauses = {
            "created_desc": "created_at DESC",
            "created_asc": "created_at ASC",
            "last_applied": "last_applied DESC NULLS LAST",
            "name_asc": "file_name ASC",
            "name_desc": "file_name DESC",
            "size_desc": "file_size DESC",
            "size_asc": "file_size ASC",
            "resolution": "(width * height) DESC",
            "duration": "duration DESC",
            "favorite": "is_favorite DESC, file_name ASC"
        }
        order_clause = sort_clauses.get(sort_by, "created_at DESC")
        query += f" ORDER BY {order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_wallpaper_by_id(self, wallpaper_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un wallpaper par son ID."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM wallpapers WHERE id = ?", (wallpaper_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_wallpaper_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Récupère un wallpaper par son chemin de fichier."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM wallpapers WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def toggle_favorite(self, wallpaper_id: int) -> bool:
        """Inverse l'état favori d'un wallpaper et retourne le nouvel état."""
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("SELECT is_favorite FROM wallpapers WHERE id = ?", (wallpaper_id,))
            row = cursor.fetchone()
            if not row:
                return False
            new_val = 0 if row[0] == 1 else 1
            conn.execute("UPDATE wallpapers SET is_favorite = ? WHERE id = ?", (new_val, wallpaper_id))
            return bool(new_val)

    def record_applied(self, wallpaper_id: int, monitor: str = "all") -> None:
        """Enregistre l'application d'un fond d'écran dans l'historique et met à jour le compteur."""
        conn = self._get_connection()
        now = datetime.now().isoformat()
        with conn:
            conn.execute("UPDATE wallpapers SET last_applied = ?, view_count = view_count + 1 WHERE id = ?", (now, wallpaper_id))
            conn.execute("INSERT INTO history (wallpaper_id, monitor, applied_at) VALUES (?, ?, ?)", (wallpaper_id, monitor, now))

    def update_tags(self, wallpaper_id: int, tags: str) -> None:
        """Met à jour les tags d'un wallpaper."""
        conn = self._get_connection()
        with conn:
            conn.execute("UPDATE wallpapers SET tags = ? WHERE id = ?", (tags, wallpaper_id))

    def delete_wallpaper(self, wallpaper_id: int) -> bool:
        """Supprime un wallpaper de la base de données."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM wallpapers WHERE id = ?", (wallpaper_id,))
            return True

    def get_all_tags(self) -> List[str]:
        """Retourne la liste unique de tous les tags existants."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT tags FROM wallpapers WHERE tags != ''")
        tags_set = set()
        for row in cursor.fetchall():
            for t in row[0].split(","):
                clean = t.strip()
                if clean:
                    tags_set.add(clean)
        return sorted(list(tags_set))

    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques globales sur la bibliothèque."""
        conn = self._get_connection()
        total = conn.execute("SELECT COUNT(*) FROM wallpapers").fetchone()[0]
        images = conn.execute("SELECT COUNT(*) FROM wallpapers WHERE media_type = 'image'").fetchone()[0]
        gifs = conn.execute("SELECT COUNT(*) FROM wallpapers WHERE media_type = 'gif'").fetchone()[0]
        videos = conn.execute("SELECT COUNT(*) FROM wallpapers WHERE media_type = 'video'").fetchone()[0]
        favs = conn.execute("SELECT COUNT(*) FROM wallpapers WHERE is_favorite = 1").fetchone()[0]
        total_size = conn.execute("SELECT SUM(file_size) FROM wallpapers").fetchone()[0] or 0
        return {
            "total": total,
            "images": images,
            "gifs": gifs,
            "videos": videos,
            "favorites": favs,
            "total_size_bytes": total_size
        }

    # --- Adjustments CRUD ---
    def get_adjustments(self, wallpaper_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM adjustments WHERE wallpaper_id = ?", (wallpaper_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_adjustments(self, wallpaper_id: int, adj: Dict[str, Any]) -> None:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        with conn:
            conn.execute("""
                INSERT INTO adjustments (
                    wallpaper_id, brightness, contrast, saturation, vibrance, gamma,
                    exposure, temperature, tint, sharpness, blur, grain, vignette,
                    black_and_white, sepia, crop_x, crop_y, crop_w, crop_h,
                    rotate, flip_h, flip_v, zoom, cached_output_path, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(wallpaper_id) DO UPDATE SET
                    brightness=excluded.brightness, contrast=excluded.contrast,
                    saturation=excluded.saturation, vibrance=excluded.vibrance,
                    gamma=excluded.gamma, exposure=excluded.exposure,
                    temperature=excluded.temperature, tint=excluded.tint,
                    sharpness=excluded.sharpness, blur=excluded.blur,
                    grain=excluded.grain, vignette=excluded.vignette,
                    black_and_white=excluded.black_and_white, sepia=excluded.sepia,
                    crop_x=excluded.crop_x, crop_y=excluded.crop_y,
                    crop_w=excluded.crop_w, crop_h=excluded.crop_h,
                    rotate=excluded.rotate, flip_h=excluded.flip_h,
                    flip_v=excluded.flip_v, zoom=excluded.zoom,
                    cached_output_path=excluded.cached_output_path,
                    updated_at=excluded.updated_at
            """, (
                wallpaper_id,
                adj.get("brightness", 1.0),
                adj.get("contrast", 1.0),
                adj.get("saturation", 1.0),
                adj.get("vibrance", 1.0),
                adj.get("gamma", 1.0),
                adj.get("exposure", 0.0),
                adj.get("temperature", 0.0),
                adj.get("tint", 0.0),
                adj.get("sharpness", 0.0),
                adj.get("blur", 0.0),
                adj.get("grain", 0.0),
                adj.get("vignette", 0.0),
                adj.get("black_and_white", 0),
                adj.get("sepia", 0),
                adj.get("crop_x", 0.0),
                adj.get("crop_y", 0.0),
                adj.get("crop_w", 1.0),
                adj.get("crop_h", 1.0),
                adj.get("rotate", 0),
                adj.get("flip_h", 0),
                adj.get("flip_v", 0),
                adj.get("zoom", 1.0),
                adj.get("cached_output_path", ""),
                now
            ))
            conn.execute("UPDATE wallpapers SET has_adjustments = 1 WHERE id = ?", (wallpaper_id,))

    def reset_adjustments(self, wallpaper_id: int) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM adjustments WHERE wallpaper_id = ?", (wallpaper_id,))
            conn.execute("UPDATE wallpapers SET has_adjustments = 0 WHERE id = ?", (wallpaper_id,))

    # --- Playlists CRUD ---
    def get_playlists(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT p.*, COUNT(pi.wallpaper_id) as item_count
            FROM playlists p
            LEFT JOIN playlist_items pi ON p.id = pi.playlist_id
            GROUP BY p.id
            ORDER BY p.name ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_playlist(self, playlist_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            return None
        playlist = dict(row)
        items_cur = conn.execute("""
            SELECT w.*, pi.position
            FROM playlist_items pi
            JOIN wallpapers w ON pi.wallpaper_id = w.id
            WHERE pi.playlist_id = ?
            ORDER BY pi.position ASC
        """, (playlist_id,))
        playlist["items"] = [dict(r) for r in items_cur.fetchall()]
        return playlist

    def create_playlist(self, name: str, description: str = "", icon: str = "folder", interval: int = 300, is_random: int = 0) -> int:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        with conn:
            cur = conn.execute(
                "INSERT INTO playlists (name, description, icon, interval_seconds, is_random, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, description, icon, interval, is_random, now)
            )
            return cur.lastrowid

    def update_playlist(self, playlist_id: int, data: Dict[str, Any]) -> None:
        conn = self._get_connection()
        fields = []
        params = []
        for k in ["name", "description", "icon", "interval_seconds", "is_random", "target_monitor", "schedule_time"]:
            if k in data:
                fields.append(f"{k} = ?")
                params.append(data[k])
        if fields:
            params.append(playlist_id)
            with conn:
                conn.execute(f"UPDATE playlists SET {', '.join(fields)} WHERE id = ?", params)

    def delete_playlist(self, playlist_id: int) -> bool:
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            return True

    def set_playlist_items(self, playlist_id: int, wallpaper_ids: List[int]) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM playlist_items WHERE playlist_id = ?", (playlist_id,))
            for idx, wid in enumerate(wallpaper_ids):
                conn.execute(
                    "INSERT INTO playlist_items (playlist_id, wallpaper_id, position) VALUES (?, ?, ?)",
                    (playlist_id, wid, idx)
                )

    # --- Automations CRUD ---
    def get_automations(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM automations ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]

    def add_automation(self, name: str, trigger_type: str, trigger_condition: str,
                       action_type: str, action_target: str, is_enabled: int = 1) -> int:
        conn = self._get_connection()
        with conn:
            cur = conn.execute("""
                INSERT INTO automations (name, trigger_type, trigger_condition, action_type, action_target, is_enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, trigger_type, trigger_condition, action_type, action_target, is_enabled))
            return cur.lastrowid

    def toggle_automation(self, auto_id: int, is_enabled: bool) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("UPDATE automations SET is_enabled = ? WHERE id = ?", (1 if is_enabled else 0, auto_id))

    def delete_automation(self, auto_id: int) -> bool:
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM automations WHERE id = ?", (auto_id,))
            return True

    # --- History ---
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT h.id as history_id, h.applied_at, h.monitor, w.*
            FROM history h
            JOIN wallpapers w ON h.wallpaper_id = w.id
            ORDER BY h.applied_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

# Instance globale
db = Database()
