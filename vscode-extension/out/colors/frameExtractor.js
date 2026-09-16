"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FrameExtractor = void 0;

const node_child_process = require("node:child_process");
const node_fs = require("node:fs");
const node_path = require("node:path");

class FrameExtractor {
    constructor() {
        this.cache = new Map();
        this.ffmpegCmd = this.detectFfmpeg();
    }

    detectFfmpeg() {
        // 1. Système hôte direct (ultra-rapide, zéro overhead Flatpak/bwrap)
        try {
            const sysFfmpeg = '/usr/bin/ffmpeg';
            if (node_fs.existsSync(sysFfmpeg)) {
                return { cmd: sysFfmpeg, prefixArgs: [] };
            }
            const check = node_child_process.spawnSync('which', ['ffmpeg'], { stdio: 'ignore' });
            if (check.status === 0) {
                return { cmd: 'ffmpeg', prefixArgs: [] };
            }
        } catch {}

        // 2. Wrapper local haute fidélité
        const homeDir = process.env.HOME || '';
        const userFfmpeg = node_path.join(homeDir, '.local/bin/ffmpeg-full');
        if (node_fs.existsSync(userFfmpeg)) {
            return { cmd: userFfmpeg, prefixArgs: [] };
        }

        // 3. Flatpak MPV avec codecs propriétaires
        try {
            const check = node_child_process.spawnSync('flatpak', ['info', 'io.mpv.Mpv'], { stdio: 'ignore' });
            if (check.status === 0) {
                return {
                    cmd: 'flatpak',
                    prefixArgs: ['run', '--filesystem=host', '--command=ffmpeg', 'io.mpv.Mpv']
                };
            }
        } catch {}

        // 4. Flatpak Celluloid
        try {
            const check = node_child_process.spawnSync('flatpak', ['info', 'io.github.celluloid_player.Celluloid'], { stdio: 'ignore' });
            if (check.status === 0) {
                return {
                    cmd: 'flatpak',
                    prefixArgs: ['run', '--filesystem=host', '--command=ffmpeg', 'io.github.celluloid_player.Celluloid']
                };
            }
        } catch {}

        // 5. Fallback système
        return { cmd: 'ffmpeg', prefixArgs: [] };
    }

    isImageFile(filePath) {
        const ext = node_path.extname(filePath).toLowerCase();
        return ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.avif', '.tiff'].includes(ext);
    }

    /**
     * Extrait les pixels RGB24 d'un fichier vidéo ou image.
     * @param filePath Chemin du média
     * @param timestamp Chaîne de temps (ex: "00:00:01" ou float secondes)
     * @param width Largeur de réduction
     * @param height Hauteur de réduction
     */
    extractFrameRgb(filePath, timestamp = 1.0, width = 80, height = 45) {
        return new Promise((resolve, reject) => {
            if (!node_fs.existsSync(filePath)) {
                return reject(new Error(`Fichier introuvable: ${filePath}`));
            }

            const isImage = this.isImageFile(filePath);
            const tsStr = typeof timestamp === 'number' ? `${timestamp.toFixed(2)}` : timestamp;
            const cacheKey = `${filePath}:${isImage ? 'img' : tsStr}:${width}x${height}`;

            if (this.cache.has(cacheKey)) {
                return resolve(this.cache.get(cacheKey));
            }

            const args = [...this.ffmpegCmd.prefixArgs];
            if (!isImage) {
                args.push('-ss', tsStr);
            }
            args.push(
                '-i', filePath,
                '-vframes', '1',
                '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', `${width}x${height}`,
                'pipe:1'
            );

            const proc = node_child_process.spawn(this.ffmpegCmd.cmd, args, {
                stdio: ['ignore', 'pipe', 'ignore']
            });

            const chunks = [];
            proc.stdout.on('data', (chunk) => chunks.push(chunk));

            const timeoutId = setTimeout(() => {
                try { proc.kill('SIGKILL'); } catch {}
                reject(new Error('Délai dépassé lors de l extraction de frame ffmpeg'));
            }, 5000);

            proc.on('error', (err) => {
                clearTimeout(timeoutId);
                reject(err);
            });

            proc.on('close', (code) => {
                clearTimeout(timeoutId);
                if (code === 0 && chunks.length > 0) {
                    const buffer = Buffer.concat(chunks);
                    // Garde en cache les 20 dernières frames
                    if (this.cache.size > 20) {
                        const firstKey = this.cache.keys().next().value;
                        this.cache.delete(firstKey);
                    }
                    this.cache.set(cacheKey, buffer);
                    resolve(buffer);
                } else {
                    reject(new Error(`FFmpeg a échoué avec le code de sortie ${code}`));
                }
            });
        });
    }
}

exports.FrameExtractor = FrameExtractor;
