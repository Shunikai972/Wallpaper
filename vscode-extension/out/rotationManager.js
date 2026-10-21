"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RotationManager = void 0;

const fs = require('fs');
const path = require('path');
let vscode = null;
try {
    vscode = require('vscode');
} catch (e) {
    vscode = null;
}

class RotationManager {
    constructor(onApplyWallpaper) {
        this.onApplyWallpaper = onApplyWallpaper;
        this.home = process.env.HOME || (process.env.USER ? (fs.existsSync('/var/home/' + process.env.USER) ? '/var/home/' + process.env.USER : '/home/' + process.env.USER) : '');
        this.settings = {
            enabled: false,
            intervalMinutes: 5,
            folder: this.detectDefaultFolder(),
            order: 'random',
            lastWallpaper: '',
            lastIndex: -1
        };
        this.nextChangeTimestamp = 0;
        this.timer = null;
        this.listeners = new Set();
        this.envWatcher = null;
    }

    /**
     * Recherche dynamique du dossier du projet WallpaperMaison
     */
    findProjectDir() {
        if (process.env.WALLPAPERMAISON_DIR && fs.existsSync(process.env.WALLPAPERMAISON_DIR)) {
            return process.env.WALLPAPERMAISON_DIR;
        }
        const home = this.home;
        const candidates = [
            path.join(home, 'Wallpaper'),
            path.join(home, 'Bureau/Wallpaper'),
            path.join(home, 'Desktop/Wallpaper'),
            path.join(home, 'reseau/Perso/Bureau/Wallpaper'),
            path.join(home, 'reseau/Perso/Wallpaper'),
            path.join('/var/home', process.env.USER || '', 'Wallpaper'),
            path.join('/var/home', process.env.USER || '', 'Bureau/Wallpaper'),
            path.join('/var/home', process.env.USER || '', 'reseau/Perso/Bureau/Wallpaper')
        ];
        for (const c of candidates) {
            if (c && fs.existsSync(path.join(c, 'scripts/patch_vscode_html.py'))) {
                return c;
            }
        }
        return '';
    }

    /**
     * Détecte le dossier par défaut contenant des fonds d'écran
     */
    detectDefaultFolder() {
        const home = this.home;
        const candidates = [];
        const proj = this.findProjectDir();
        if (proj) {
            candidates.push(path.join(proj, 'Wallpaper'));
        }
        candidates.push(
            path.join(home, 'Wallpaper'),
            path.join(home, 'Pictures/Wallpapers'),
            path.join(home, 'Pictures'),
            path.join(home, 'reseau/Perso/Téléchargements'),
            path.join(home, 'reseau/Perso/Images/Wallpapers'),
            path.join(home, 'Téléchargements'),
            path.join(home, 'Downloads')
        );
        for (const c of candidates) {
            try {
                if (c && fs.existsSync(c)) {
                    const files = this.getWallpapers(c);
                    if (files.length > 0) return c;
                }
            } catch (e) {}
        }
        return candidates[0] || '';
    }

    /**
     * Chemins vers le fichier de paramètres JSON persistant
     */
    getSettingsPaths() {
        return [
            path.join(this.home, '.config/wallpapermaison/rotation_settings.json'),
            path.join(this.home, 'reseau/Perso/.config/wallpapermaison/rotation_settings.json')
        ];
    }

    /**
     * Chemins vers les fichiers .env candidats
     */
    getEnvPaths() {
        const paths = [];
        const proj = this.findProjectDir();
        if (proj) {
            paths.push(path.join(proj, '.env'));
        }
        paths.push(
            path.join(this.home, 'Wallpaper/.env'),
            path.join(this.home, 'Bureau/Wallpaper/.env'),
            path.join(this.home, 'Desktop/Wallpaper/.env'),
            path.join(this.home, 'reseau/Perso/Bureau/Wallpaper/.env')
        );
        return paths;
    }

    /**
     * Charge les réglages depuis rotation_settings.json et .env
     */
    loadSettings() {
        let jsonLoaded = false;
        for (const p of this.getSettingsPaths()) {
            try {
                if (fs.existsSync(p)) {
                    const raw = fs.readFileSync(p, 'utf8');
                    const data = JSON.parse(raw);
                    if (data) {
                        if (typeof data.enabled === 'boolean') this.settings.enabled = data.enabled;
                        if (typeof data.intervalMinutes === 'number' && data.intervalMinutes >= 1) {
                            this.settings.intervalMinutes = data.intervalMinutes;
                        } else if (typeof data.interval_minutes === 'number' && data.interval_minutes >= 1) {
                            this.settings.intervalMinutes = data.interval_minutes;
                        }
                        if (data.folder && fs.existsSync(data.folder)) this.settings.folder = data.folder;
                        if (data.order === 'random' || data.order === 'sequential' || data.order === 'order') {
                            this.settings.order = data.order === 'order' ? 'sequential' : data.order;
                        }
                        if (data.lastWallpaper) this.settings.lastWallpaper = data.lastWallpaper;
                        if (typeof data.lastIndex === 'number') this.settings.lastIndex = data.lastIndex;
                        jsonLoaded = true;
                        break;
                    }
                }
            } catch (e) {}
        }

        // Compléter avec .env si présent
        for (const ep of this.getEnvPaths()) {
            try {
                if (fs.existsSync(ep)) {
                    const content = fs.readFileSync(ep, 'utf8');
                    const parsed = this.parseEnv(content);
                    if (parsed.ROTATION_ENABLED !== undefined) {
                        this.settings.enabled = (parsed.ROTATION_ENABLED.toLowerCase() === 'true' || parsed.ROTATION_ENABLED === '1');
                    }
                    if (parsed.ROTATION_INTERVAL_MINUTES) {
                        const m = parseInt(parsed.ROTATION_INTERVAL_MINUTES, 10);
                        if (!isNaN(m) && m >= 1) this.settings.intervalMinutes = m;
                    }
                    if (parsed.ROTATION_FOLDER) {
                        let rf = parsed.ROTATION_FOLDER.trim();
                        if (!path.isAbsolute(rf)) {
                            rf = path.resolve(path.dirname(ep), rf);
                        }
                        if (fs.existsSync(rf)) {
                            this.settings.folder = rf;
                        }
                    }
                    if (parsed.ROTATION_ORDER) {
                        const ord = parsed.ROTATION_ORDER.toLowerCase().trim();
                        if (ord === 'random' || ord === 'sequential' || ord === 'order') {
                            this.settings.order = ord === 'order' ? 'sequential' : ord;
                        }
                    }
                    break;
                }
            } catch (e) {}
        }

        // Dossier de secours si le dossier actuel n'existe pas
        if (!this.settings.folder || !fs.existsSync(this.settings.folder)) {
            this.settings.folder = this.detectDefaultFolder();
        }

        if (this.settings.enabled) {
            this.startTimer();
        } else {
            this.stopTimer();
        }
        this.notifyListeners();
        return this.settings;
    }

    /**
     * Sauvegarde les réglages dans rotation_settings.json et .env
     */
    saveSettings(newSettings = {}) {
        Object.assign(this.settings, newSettings);
        if (this.settings.order === 'order') this.settings.order = 'sequential';

        // 1. Sauvegarde dans les fichiers JSON persistants
        const payload = JSON.stringify({
            enabled: this.settings.enabled,
            intervalMinutes: this.settings.intervalMinutes,
            folder: this.settings.folder,
            order: this.settings.order,
            lastWallpaper: this.settings.lastWallpaper,
            lastIndex: this.settings.lastIndex,
            updatedAt: Date.now() / 1000
        }, null, 2);

        for (const sp of this.getSettingsPaths()) {
            try {
                const dir = path.dirname(sp);
                if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                fs.writeFileSync(sp, payload, 'utf8');
            } catch (e) {}
        }

        // 2. Synchronisation dans le fichier .env
        const envUpdates = {
            ROTATION_ENABLED: this.settings.enabled ? 'true' : 'false',
            ROTATION_INTERVAL_MINUTES: String(this.settings.intervalMinutes),
            ROTATION_FOLDER: this.settings.folder,
            ROTATION_ORDER: this.settings.order
        };
        for (const ep of this.getEnvPaths()) {
            try {
                if (fs.existsSync(ep)) {
                    this.updateEnvFile(ep, envUpdates);
                    break;
                }
            } catch (e) {}
        }

        // 3. Mise à jour de l'état du timer
        if (this.settings.enabled) {
            this.startTimer();
        } else {
            this.stopTimer();
        }

        this.notifyListeners();
        return this.settings;
    }

    parseEnv(content) {
        const res = {};
        for (const line of content.split('\n')) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;
            const eq = trimmed.indexOf('=');
            if (eq > 0) {
                const k = trimmed.slice(0, eq).trim();
                let v = trimmed.slice(eq + 1).trim();
                if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
                    v = v.slice(1, -1);
                }
                res[k] = v;
            }
        }
        return res;
    }

    updateEnvFile(envPath, updates) {
        let lines = [];
        if (fs.existsSync(envPath)) {
            lines = fs.readFileSync(envPath, 'utf8').split('\n');
        }
        const keysFound = new Set();
        const newLines = lines.map(line => {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) return line;
            const eq = line.indexOf('=');
            if (eq === -1) return line;
            const key = line.slice(0, eq).trim();
            if (updates.hasOwnProperty(key)) {
                keysFound.add(key);
                let val = updates[key];
                if (typeof val === 'string' && (val.includes(' ') || val.includes('/'))) {
                    val = `"${val}"`;
                }
                return `${key}=${val}`;
            }
            return line;
        });

        for (const key of Object.keys(updates)) {
            if (!keysFound.has(key)) {
                let val = updates[key];
                if (typeof val === 'string' && (val.includes(' ') || val.includes('/'))) {
                    val = `"${val}"`;
                }
                newLines.push(`${key}=${val}`);
            }
        }
        fs.writeFileSync(envPath, newLines.join('\n'), 'utf8');
    }

    /**
     * Récupère les fichiers multimédias compatibles dans un dossier
     */
    getWallpapers(folderPath) {
        if (!folderPath || !fs.existsSync(folderPath)) return [];
        try {
            const VALID_EXTS = new Set(['.mp4', '.webm', '.mkv', '.mov', '.png', '.jpg', '.jpeg', '.webp', '.gif']);
            const entries = fs.readdirSync(folderPath, { withFileTypes: true });
            const files = [];
            for (const entry of entries) {
                if (!entry.isFile() && !entry.isSymbolicLink()) continue;
                const name = entry.name;
                if (name.startsWith('.') || name.endsWith('.part') || name === 'wallpaper.mp4') continue;
                const ext = path.extname(name).toLowerCase();
                if (VALID_EXTS.has(ext)) {
                    files.push({
                        path: path.join(folderPath, name),
                        name: name,
                        isVideo: ['.mp4', '.webm', '.mkv', '.mov'].includes(ext),
                        ext: ext
                    });
                }
            }
            return files.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
        } catch (e) {
            return [];
        }
    }

    getStats(folderPath) {
        const files = this.getWallpapers(folderPath);
        const videoCount = files.filter(f => f.isVideo).length;
        const imageCount = files.length - videoCount;
        return {
            total: files.length,
            videoCount: videoCount,
            imageCount: imageCount,
            files: files
        };
    }

    startTimer() {
        if (this.nextChangeTimestamp <= Date.now()) {
            this.nextChangeTimestamp = Date.now() + (this.settings.intervalMinutes * 60 * 1000);
        }

        if (this.timer) clearInterval(this.timer);
        this.timer = setInterval(() => {
            if (!this.settings.enabled) return;

            const now = Date.now();
            if (now >= this.nextChangeTimestamp) {
                this.nextWallpaper();
            } else {
                this.notifyListeners();
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
        this.nextChangeTimestamp = 0;
        this.notifyListeners();
    }

    getTimeRemaining() {
        if (!this.settings.enabled || this.nextChangeTimestamp === 0) return 0;
        return Math.max(0, Math.ceil((this.nextChangeTimestamp - Date.now()) / 1000));
    }

    formatTimeRemaining() {
        const sec = this.getTimeRemaining();
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    /**
     * Déclenche immédiatement le passage au fond d'écran suivant
     */
    async nextWallpaper() {
        const files = this.getWallpapers(this.settings.folder);
        if (files.length === 0) {
            if (vscode && vscode.window) {
                vscode.window.showWarningMessage(`Aucun fond d'écran compatible trouvé dans : ${this.settings.folder}`);
            }
            this.nextChangeTimestamp = Date.now() + (this.settings.intervalMinutes * 60 * 1000);
            this.notifyListeners();
            return null;
        }

        let chosen = null;
        if (files.length === 1) {
            chosen = files[0];
        } else if (this.settings.order === 'random') {
            const candidates = files.filter(f => f.path !== this.settings.lastWallpaper);
            const pool = candidates.length > 0 ? candidates : files;
            const randomIndex = Math.floor(Math.random() * pool.length);
            chosen = pool[randomIndex];
            this.settings.lastIndex = files.findIndex(f => f.path === chosen.path);
        } else {
            // Séquentiel (Dans l'ordre)
            let curIdx = files.findIndex(f => f.path === this.settings.lastWallpaper);
            if (curIdx === -1) {
                curIdx = this.settings.lastIndex >= 0 ? this.settings.lastIndex : -1;
            }
            const nextIdx = (curIdx + 1) % files.length;
            chosen = files[nextIdx];
            this.settings.lastIndex = nextIdx;
        }

        if (chosen) {
            this.settings.lastWallpaper = chosen.path;
            this.nextChangeTimestamp = Date.now() + (this.settings.intervalMinutes * 60 * 1000);
            this.saveSettings({
                lastWallpaper: chosen.path,
                lastIndex: this.settings.lastIndex
            });

            if (typeof this.onApplyWallpaper === 'function') {
                await this.onApplyWallpaper(chosen.path, chosen.isVideo ? 'video' : 'image');
            }
            if (vscode && vscode.window) {
                vscode.window.setStatusBarMessage(`🔄 Rotation : ${chosen.name}`, 4000);
            }
            this.notifyListeners();
            return chosen.path;
        }
        return null;
    }

    addListener(fn) {
        this.listeners.add(fn);
    }

    removeListener(fn) {
        this.listeners.delete(fn);
    }

    notifyListeners() {
        const state = this.getState();
        for (const fn of this.listeners) {
            try { fn(state); } catch (e) {}
        }
    }

    getState() {
        const stats = this.getStats(this.settings.folder);
        return {
            enabled: this.settings.enabled,
            intervalMinutes: this.settings.intervalMinutes,
            folder: this.settings.folder,
            order: this.settings.order,
            lastWallpaper: this.settings.lastWallpaper,
            timeRemaining: this.getTimeRemaining(),
            timeRemainingFormatted: this.formatTimeRemaining(),
            totalCount: stats.total,
            videoCount: stats.videoCount,
            imageCount: stats.imageCount
        };
    }
}

exports.RotationManager = RotationManager;
