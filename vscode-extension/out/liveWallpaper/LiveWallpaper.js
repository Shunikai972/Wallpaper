"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.LiveWallpaper = void 0;
const node_fs_1 = __importDefault(require("node:fs"));
const vscode_1 = __importDefault(require("vscode"));
const constants_1 = require("../utils/constants");
const vscodePath_1 = require("../utils/vscodePath");
const vsHelp_1 = require("../utils/vsHelp");
const PatchFile_1 = require("./PatchFile");
const PatchGenerator_1 = require("./PatchGenerator");
const colorEngine_1 = require("../colors/colorEngine");
/** Default configuration values */
const DEFAULTS = {
    videoPath: '',
    opacity: 0.1,
    size: 'cover',
    loop: true,
    enabled: true,
};
/**
 * Main extension logic for Live Wallpaper.
 *
 * Manages the lifecycle of the video wallpaper patch applied to
 * VSCode's workbench.html file.
 */
class LiveWallpaper {
    /** The HTML file we patch */
    htmlFile = new PatchFile_1.HtmlPatchFile(vscodePath_1.vscodePath.workbenchHtmlPath);
    /** Color synchronization engine */
    colorEngine = new colorEngine_1.ColorEngine();
    /** Subscriptions to dispose when extension deactivates */
    disposables = [];
    /** Current user configuration — reads the whole flat object */
    getRawConfig() {
        const cfg = vscode_1.default.workspace.getConfiguration();
        return cfg.get(constants_1.CONFIG_SECTION) ?? {};
    }
    /** Write the full config object back to settings.json */
    async writeConfig(values) {
        const cfg = vscode_1.default.workspace.getConfiguration();
        await cfg.update(constants_1.CONFIG_SECTION, values, vscode_1.default.ConfigurationTarget.Global);
    }
    // ─────────────────────────────────────────────────────────────────────────
    // Private helpers
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * Write the touch file on first install.
     * The touch file records the workbench.html path so the uninstall hook
     * can clean up even when the VSCode API is unavailable.
     */
    async checkFirstLoad() {
        const firstLoad = !node_fs_1.default.existsSync(constants_1.TOUCH_FILE_PATH);
        if (firstLoad) {
            await node_fs_1.default.promises.writeFile(constants_1.TOUCH_FILE_PATH, vscodePath_1.vscodePath.workbenchHtmlPath, constants_1.ENCODING);
            return true;
        }
        return false;
    }
    /**
     * Build the LiveWallpaperConfig from current user settings,
     * normalizing the video path for the VSCode sandbox.
     */
    buildConfig() {
        const raw = this.getRawConfig();
        const rawPath = typeof raw.videoPath === 'string' ? raw.videoPath : '';
        const opacity = typeof raw.opacity === 'number' ? raw.opacity : DEFAULTS.opacity;
        const size = typeof raw.size === 'string' &&
            ['cover', 'contain', 'fill', 'auto'].includes(raw.size)
            ? raw.size
            : DEFAULTS.size;
        const loop = typeof raw.loop === 'boolean' ? raw.loop : DEFAULTS.loop;
        const enabled = typeof raw.enabled === 'boolean' ? raw.enabled : DEFAULTS.enabled;
        return {
            videoPath: vsHelp_1.vsHelp.normalizeVideoPath(rawPath),
            // Clamp user value to [0.1, 1.0] then scale to max 80% CSS opacity
            // so the UI stays readable even at the maximum setting.
            opacity: Math.round(Math.min(1.0, Math.max(0.1, opacity)) * 0.8 * 100) /
                100,
            size,
            loop,
            enabled,
        };
    }
    /**
     * Called when the user changes a setting in settings.json.
     * Prompts to apply the new config or disable.
     */
    async onConfigChange(event) {
        if (event && event.affectsConfiguration('liveWallpaper.colors')) {
            await this.colorEngine.start();
            return;
        }
        if (event && event.affectsConfiguration('liveWallpaper.videoPath')) {
            await this.colorEngine.start();
            return;
        }

        await this.colorEngine.start();

        const hasInstalled = await this.hasInstalled();
        const { enabled } = this.buildConfig();

        let isWritable = false;
        try {
            if (node_fs_1.default.existsSync(this.htmlFile.filePath)) {
                node_fs_1.default.accessSync(this.htmlFile.filePath, node_fs_1.default.constants.W_OK);
                isWritable = true;
            }
        } catch {}

        if (!isWritable) {
            return;
        }

        if (!enabled) {
            if (hasInstalled) {
                vsHelp_1.vsHelp.reload({
                    message: 'Live Wallpaper will be disabled.',
                    btnReload: 'Disable and Reload',
                    beforeReload: () => this.uninstall(),
                });
            }
            return;
        }
        vsHelp_1.vsHelp.reload({
            message: 'Live Wallpaper: Configuration changed — click to apply.',
            btnReload: 'Apply and Reload',
            beforeReload: () => this.applyPatch(),
        });
    }
    // ─────────────────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * Initialize the extension:
     *  1. Write touch file on first install
     *  2. If disabled but patch still exists → silently remove and reload
     *  3. If enabled and patch needs updating → prompt to apply
     *  4. Start listening for config changes
     */
    async setup() {
        await this.checkFirstLoad();
        const patchType = await this.htmlFile.getPatchType();
        const hasInstalled = await this.hasInstalled();
        const { enabled, videoPath } = this.buildConfig();
        // ── Safety net: patch is in workbench.html but enabled=false ──────────
        if (!enabled && hasInstalled) {
            await this.uninstall();
            return;
        }
        const needsUpdate = [
            PatchFile_1.EFilePatchType.Legacy,
            PatchFile_1.EFilePatchType.None,
        ].includes(patchType);

        let isWritable = false;
        try {
            if (node_fs_1.default.existsSync(this.htmlFile.filePath)) {
                node_fs_1.default.accessSync(this.htmlFile.filePath, node_fs_1.default.constants.W_OK);
                isWritable = true;
            }
        } catch {}

        if (isWritable && enabled && videoPath && needsUpdate) {
            vscode_1.default.window
                .showInformationMessage(`Live Wallpaper v${constants_1.VERSION} is ready! Apply to activate the video background.`, { title: 'Apply and Reload' }, { title: 'Skip' })
                .then(async (choice) => {
                if (choice?.title === 'Apply and Reload') {
                    await this.applyPatch();
                    await vscode_1.default.commands.executeCommand('workbench.action.reloadWindow');
                }
            });
        }

        // Lancer immédiatement le moteur de couleurs dynamiques
        try {
            await this.colorEngine.start();
        } catch (err) {
            console.error("Live Wallpaper: Erreur démarrage ColorEngine:", err);
        }

        // Watch for configuration changes
        this.disposables.push(vscode_1.default.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration(constants_1.CONFIG_SECTION)) {
                this.onConfigChange(event);
            }
        }));
    }
    /**
     * Apply the video wallpaper patch to workbench.html.
     * @returns true if the patch was written successfully
     */
    async applyPatch() {
        const config = this.buildConfig();
        if (!config.enabled) {
            return false;
        }
        if (!config.videoPath) {
            vscode_1.default.window.showWarningMessage('Live Wallpaper: No video path set. Please configure `liveWallpaper.videoPath` in your settings.');
            return false;
        }
        // Verify the workbench.html path is accessible
        const fs = await import('node:fs');
        if (!fs.existsSync(this.htmlFile.filePath)) {
            vscode_1.default.window.showErrorMessage(`Live Wallpaper: Cannot find VSCode workbench.html at:\n${this.htmlFile.filePath}\n\nPlease report this issue.`);
            return false;
        }
        const script = PatchGenerator_1.PatchGenerator.create(config);
        return this.htmlFile.applyPatches(script);
    }
    /**
     * Check whether the patch is currently applied to workbench.html.
     */
    hasInstalled() {
        return this.htmlFile.hasPatched();
    }
    /**
     * Remove the wallpaper patch from workbench.html.
     * @returns true if the restore succeeded
     */
    async uninstall() {
        return this.htmlFile.restore();
    }
    /**
     * Reset all settings to their default values and remove the patch.
     */
    async reset() {
        await this.colorEngine.reset();
        await this.writeConfig(undefined);
        await this.uninstall();
    }
    /**
     * Merge a partial update into the existing flat config object.
     * Used by commands that only need to change one field (e.g. enabled).
     */
    async updateConfig(patch) {
        const current = this.getRawConfig();
        await this.writeConfig({ ...current, ...patch });
    }
    /** Release all subscriptions */
    dispose() {
        this.colorEngine.dispose();
        this.disposables.forEach((d) => {
            d.dispose();
        });
    }
}
exports.LiveWallpaper = LiveWallpaper;
//# sourceMappingURL=LiveWallpaper.js.map