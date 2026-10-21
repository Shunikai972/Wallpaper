"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WallpaperBridge = void 0;

const node_child_process = require("node:child_process");
const node_fs = require("node:fs");
const node_path = require("node:path");

class WallpaperBridge {
    static getHomeDir() {
        return process.env.HOME || '';
    }

    static getWallpaperMaisonDbPaths() {
        const home = this.getHomeDir();
        return [
            node_path.join(home, 'reseau/Perso/.local/share/wallpapermaison/wallpapermaison.db'),
            node_path.join(home, '.local/share/wallpapermaison/wallpapermaison.db')
        ];
    }

    /**
     * Détecte automatiquement le fond d'écran actif de la session ou de WallpaperMaison.
     */
    static detectCurrentWallpaper() {
        // 0. Détection prioritaire via current_wallpaper.json (WallpaperMaison actif)
        try {
            const home = this.getHomeDir();
            const candidates = [
                node_path.join(home, '.config/wallpapermaison/current_wallpaper.json'),
                node_path.join(home, 'reseau/Perso/.config/wallpapermaison/current_wallpaper.json')
            ];
            for (const c of candidates) {
                if (node_fs.existsSync(c)) {
                    const data = JSON.parse(node_fs.readFileSync(c, 'utf8'));
                    if (data && data.path && node_fs.existsSync(data.path)) {
                        return data.path;
                    }
                }
            }
        } catch {}

        // 1. Détection via GSettings Hanabi (fond vidéo animé natif GNOME)
        try {
            const out = node_child_process.execFileSync('gsettings', ['get', 'io.github.jeffshee.hanabi-extension', 'video-path'], {
                encoding: 'utf-8',
                stdio: ['ignore', 'pipe', 'ignore']
            }).trim();
            const cleaned = out.replace(/^['"]/, '').replace(/['"]$/, '');
            if (cleaned && node_fs.existsSync(cleaned)) {
                return cleaned;
            }
        } catch {}

        // 2. Détection via GSettings GNOME (image statique)
        try {
            const out = node_child_process.execFileSync('gsettings', ['get', 'org.gnome.desktop.background', 'picture-uri'], {
                encoding: 'utf-8',
                stdio: ['ignore', 'pipe', 'ignore']
            }).trim();
            const cleaned = out.replace(/^'file:\/\//, '').replace(/'$/, '');
            if (cleaned && node_fs.existsSync(cleaned)) {
                // Si c'est une miniature de vidéo, on cherche si la vidéo d'origine est connue
                const videoOriginal = this.findOriginalVideoForThumbnail(cleaned);
                if (videoOriginal && node_fs.existsSync(videoOriginal)) {
                    return videoOriginal;
                }
                return cleaned;
            }
        } catch {}

        // 2. Détection via la base de données WallpaperMaison (si Python/sqlite3 dispo)
        const dbPaths = this.getWallpaperMaisonDbPaths();
        for (const dbPath of dbPaths) {
            if (node_fs.existsSync(dbPath)) {
                try {
                    const pyCode = `
import sqlite3
conn = sqlite3.connect("${dbPath}")
c = conn.cursor()
row = c.execute("SELECT w.file_path FROM history h JOIN wallpapers w ON h.wallpaper_id = w.id ORDER BY h.applied_at DESC LIMIT 1").fetchone()
if not row:
    row = c.execute("SELECT file_path FROM wallpapers ORDER BY id DESC LIMIT 1").fetchone()
print(row[0] if row else "")
`;
                    const pyOut = node_child_process.execFileSync('python3', ['-c', pyCode], {
                        encoding: 'utf-8',
                        stdio: ['ignore', 'pipe', 'ignore']
                    }).trim();
                    if (pyOut && node_fs.existsSync(pyOut)) {
                        return pyOut;
                    }
                } catch {}
            }
        }

        // 3. Fallback sur le dossier Wallpaper du projet
        const homeDir = this.getHomeDir();
        const repoCandidates = [
            process.env.WALLPAPERMAISON_DIR,
            node_path.join(homeDir, 'Wallpaper'),
            node_path.join(homeDir, 'Bureau/Wallpaper'),
            node_path.join(homeDir, 'Desktop/Wallpaper'),
            node_path.join(homeDir, 'reseau/Perso/Bureau/Wallpaper')
        ];
        for (const rc of repoCandidates) {
            if (rc) {
                const wpDir = node_path.join(rc, 'Wallpaper');
                if (node_fs.existsSync(wpDir)) {
                    try {
                        const files = node_fs.readdirSync(wpDir).filter(f => ['.mp4', '.webm'].some(ext => f.toLowerCase().endsWith(ext)));
                        if (files.length > 0) {
                            return node_path.join(wpDir, files[0]);
                        }
                    } catch {}
                }
            }
        }

        return null;
    }

    static findOriginalVideoForThumbnail(thumbPath) {
        // Si thumbPath est dans .cache/wallpapermaison/thumbnails/<hash>.jpg
        // on peut chercher dans la base SQLite de WallpaperMaison
        const dbPaths = this.getWallpaperMaisonDbPaths();
        for (const dbPath of dbPaths) {
            if (node_fs.existsSync(dbPath)) {
                try {
                    const pyCode = `
import sqlite3
conn = sqlite3.connect("${dbPath}")
c = conn.cursor()
row = c.execute("SELECT file_path FROM wallpapers WHERE thumbnail_path = ?", ("${thumbPath}",)).fetchone()
print(row[0] if row else "")
`;
                    const pyOut = node_child_process.execFileSync('python3', ['-c', pyCode], {
                        encoding: 'utf-8',
                        stdio: ['ignore', 'pipe', 'ignore']
                    }).trim();
                    if (pyOut && node_fs.existsSync(pyOut)) {
                        return pyOut;
                    }
                } catch {}
            }
        }
        return null;
    }
}

exports.WallpaperBridge = WallpaperBridge;
