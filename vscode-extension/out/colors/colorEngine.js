"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ColorEngine = void 0;

const vscode_1 = __importDefault(require("vscode"));
const colorimetry_1 = require("./colorimetry");
const frameExtractor_1 = require("./frameExtractor");
const temporalSmoother_1 = require("./temporalSmoother");
const themeSynchronizer_1 = require("./themeSynchronizer");
const wallpaperBridge_1 = require("./wallpaperBridge");

class ColorEngine {
    constructor() {
        this.extractor = new frameExtractor_1.FrameExtractor();
        this.smoother = new temporalSmoother_1.TemporalSmoother();
        this.synchronizer = new themeSynchronizer_1.ThemeSynchronizer();
        this.outputChannel = vscode_1.default.window.createOutputChannel("Live Wallpaper Colors");

        this.timer = null;
        this.currentVideoTime = 0.0;
        this.activeMediaFile = null;
        this.isProcessing = false;
        this.lastPalette = null;
    }

    log(msg) {
        const cfg = this.getConfig();
        if (cfg.debug) {
            const time = new Date().toISOString().substring(11, 19);
            this.outputChannel.appendLine(`[${time}] ${msg}`);
        }
    }

    getConfig() {
        const rootCfg = vscode_1.default.workspace.getConfiguration("liveWallpaper");
        const colorsCfg = rootCfg.get("colors") || {};

        return {
            enabled: typeof colorsCfg.enabled === 'boolean' ? colorsCfg.enabled : true,
            mode: colorsCfg.mode || "auto",
            updateInterval: typeof colorsCfg.updateInterval === 'number'
                ? (colorsCfg.updateInterval >= 50 ? colorsCfg.updateInterval / 1000 : Math.max(0.5, colorsCfg.updateInterval))
                : 2.5,
            smoothing: typeof colorsCfg.smoothing === 'number' ? colorsCfg.smoothing : 0.25,
            changeThreshold: typeof colorsCfg.changeThreshold === 'number' ? colorsCfg.changeThreshold : 4.0,
            saturation: typeof colorsCfg.saturation === 'number' ? colorsCfg.saturation : 1.0,
            brightness: typeof colorsCfg.brightness === 'number' ? colorsCfg.brightness : 1.0,
            contrast: typeof colorsCfg.contrast === 'number' ? colorsCfg.contrast : 7.0,
            analysisResolution: colorsCfg.analysisResolution || "160x90",
            debug: typeof colorsCfg.debug === 'boolean' ? colorsCfg.debug : false,
            syncWithWallpaperMaison: rootCfg.get("syncWithWallpaperMaison") ?? true,
            configuredVideoPath: rootCfg.get("videoPath") || ""
        };
    }

    resolveMediaPath() {
        const cfg = this.getConfig();
        if (cfg.configuredVideoPath && cfg.configuredVideoPath.trim().length > 0) {
            let p = cfg.configuredVideoPath.trim();
            p = p.replace(/^file:\/\//, '').replace(/^vscode-file:\/\/vscode-app\/?/, '/');
            return p;
        }

        if (cfg.syncWithWallpaperMaison) {
            const detected = wallpaperBridge_1.WallpaperBridge.detectCurrentWallpaper();
            if (detected) {
                return detected;
            }
        }
        return null;
    }

    async start() {
        this.stop();
        const cfg = this.getConfig();
        if (!cfg.enabled) {
            this.log("Système de couleurs dynamiques désactivé dans la configuration.");
            await this.synchronizer.clear();
            return;
        }

        this.smoother.setSmoothing(cfg.smoothing);
        this.smoother.setChangeThreshold(cfg.changeThreshold);

        const mediaPath = this.resolveMediaPath();
        if (!mediaPath) {
            this.log("Aucun média spécifié ou détecté pour l analyse colorimétrique.");
            return;
        }

        this.activeMediaFile = mediaPath;
        this.log(`Démarrage de l analyse couleur sur : ${mediaPath} (Mode: ${cfg.mode})`);

        // Premier passage immédiat
        await this.processFrame(true);

        if (cfg.mode === "static") {
            // Mode static : une seule analyse
            return;
        }

        // Mode dynamic ou periodic : intervalle de polling
        const intervalMs = Math.round(cfg.updateInterval * 1000);
        this.timer = setInterval(async () => {
            await this.processFrame(false);
        }, intervalMs);
    }

    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
        this.isProcessing = false;
    }

    async processFrame(force = false) {
        if (this.isProcessing) return;
        this.isProcessing = true;

        try {
            const cfg = this.getConfig();
            const currentMedia = this.resolveMediaPath();

            if (!currentMedia) {
                this.isProcessing = false;
                return;
            }

            // Détection de changement de fond d'écran
            if (currentMedia !== this.activeMediaFile) {
                this.activeMediaFile = currentMedia;
                this.currentVideoTime = 0.0;
                force = true;
                this.log(`Changement de fond détecté -> ${currentMedia}`);
            }

            const [resW, resH] = cfg.analysisResolution.split('x').map(n => parseInt(n) || 80);

            // Avancement du timestamp pour les vidéos
            if (!this.extractor.isImageFile(this.activeMediaFile)) {
                this.currentVideoTime += cfg.updateInterval;
                // Boucle arbitraire à 120s pour la progression des frames
                if (this.currentVideoTime > 300) this.currentVideoTime = 0.0;
            } else {
                this.currentVideoTime = 0.0;
            }

            const rgbBuffer = await this.extractor.extractFrameRgb(
                this.activeMediaFile,
                this.currentVideoTime,
                resW,
                resH
            );

            if (!rgbBuffer || rgbBuffer.length < 3) {
                this.isProcessing = false;
                return;
            }

            const extractedPalette = colorimetry_1.Colorimetry.extractPalette(
                rgbBuffer,
                resW,
                resH,
                { saturation: cfg.saturation, contrast: cfg.contrast, mode: cfg.mode }
            );

            const smoothed = this.smoother.smooth(extractedPalette, force);
            if (smoothed) {
                this.lastPalette = smoothed;
                const modeParam = (cfg.mode === "accent-only") ? "accent-only" : "full";
                await this.synchronizer.apply(smoothed, modeParam);
                this.log(`Palette appliquée (Contraste: ${smoothed.contrastRatio.toFixed(1)}:1) | Dom: ${smoothed.dominant} | Acc: ${smoothed.accent}`);
            }
        } catch (err) {
            this.log(`Erreur lors du traitement colorimétrique : ${err.message}`);
        } finally {
            this.isProcessing = false;
        }
    }

    async forceExtractNow() {
        this.log("Extraction manuelle immédiate demandée...");
        await this.processFrame(true);
    }

    async reset() {
        this.stop();
        this.smoother.reset();
        await this.synchronizer.clear();
        this.lastPalette = null;
        this.log("Système de couleurs réinitialisé.");
    }

    dispose() {
        this.stop();
        this.synchronizer.clear();
        this.outputChannel.dispose();
    }
}

exports.ColorEngine = ColorEngine;
