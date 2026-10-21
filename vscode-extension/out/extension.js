"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const vscode_1 = __importDefault(require("vscode"));
const liveWallpaper_1 = require("./liveWallpaper");
const constants_1 = require("./utils/constants");
const vsHelp_1 = require("./utils/vsHelp");
/**
 * Create and show the status bar item that provides quick access to commands.
 */
function createStatusBar() {
    const item = vscode_1.default.window.createStatusBarItem(vscode_1.default.StatusBarAlignment.Right, 100);
    item.command = 'liveWallpaper.showCommands';
    item.name = 'Live Wallpaper';
    item.text = '$(play-circle) Live Wallpaper';
    item.tooltip = 'Show Live Wallpaper commands';
    item.show();
    return item;
}
/**
 * Extension activation entry point.
 * Called once when VSCode starts (onStartupFinished).
 *
 * IMPORTANT: Commands are registered FIRST before any async work,
 * so they are always available even if setup() encounters an error.
 */
async function activate(context) {
    const wallpaper = new liveWallpaper_1.LiveWallpaper();
    context.subscriptions.push(wallpaper);
    // ── Commands — registered immediately so they are always available ─────
    /** Apply the wallpaper patch and reload */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.apply', async () => {
        await wallpaper.updateConfig({ enabled: true });
        const ok = await wallpaper.applyPatch();
        if (ok) {
            await vsHelp_1.vsHelp.reload();
        }
    }));
    /** Enable the wallpaper (set enabled=true) and apply patch, then reload */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.enable', async () => {
        await wallpaper.updateConfig({ enabled: true });
        const ok = await wallpaper.applyPatch();
        if (ok) {
            await vsHelp_1.vsHelp.reload();
        }
        else {
            vscode_1.default.window.showWarningMessage('Live Wallpaper: Could not enable — make sure `liveWallpaper.videoPath` is set in your settings.');
        }
    }));
    /** Disable the wallpaper: removes the patch then reloads once */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.disable', async () => {
        await wallpaper.updateConfig({ enabled: false });
        await wallpaper.uninstall(); // must happen before reload so the patch is gone
        await vsHelp_1.vsHelp.reload();
    }));
    /** Reset all settings to defaults, remove patch, and reload */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.reset', async () => {
        const confirm = await vscode_1.default.window.showWarningMessage('Live Wallpaper: Reset all settings to defaults and remove the wallpaper?', { title: 'Reset and Reload' }, { title: 'Cancel' });
        if (confirm?.title === 'Reset and Reload') {
            await wallpaper.reset();
            await vsHelp_1.vsHelp.reload();
        }
    }));
    /** Uninstall the extension entirely */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.uninstall', async () => {
        const confirm = await vscode_1.default.window.showWarningMessage('Live Wallpaper: Uninstall extension? The wallpaper patch and all settings will be removed.', { title: 'Uninstall' }, { title: 'Cancel' });
        if (confirm?.title === 'Uninstall') {
            // reset() removes both the workbench.html patch AND the settings entry
            await wallpaper.reset();
            await vscode_1.default.commands.executeCommand('workbench.extensions.uninstallExtension', constants_1.EXTENSION_ID);
            vsHelp_1.vsHelp.reload({
                message: 'Live Wallpaper has been uninstalled. Goodbye! 👋',
            });
        }
    }));
    /** Open quick-pick with all Live Wallpaper commands */
    const statusBar = createStatusBar();
    context.subscriptions.push(statusBar);
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.showCommands', () => {
        vscode_1.default.commands.executeCommand('workbench.action.quickOpen', '>Live Wallpaper: ');
    }));
    /** Create Template Setup */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.createTemplate', async () => {
        await wallpaper.updateConfig({
            videoPath: '/absolute/path/to/your/wallpaper.mp4',
            opacity: 0.1,
            size: 'cover',
            enabled: true,
            loop: true,
        });
        await vscode_1.default.commands.executeCommand('workbench.action.openSettingsJson');
        vscode_1.default.window.showInformationMessage('Live Wallpaper: Setup template created in settings.json! Please update the videoPath.');
    }));
    /** Open Wallpaper Player Webview */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.openView', () => {
        try {
            const { WebviewPlayer } = require('./liveWallpaper/WebviewPlayer');
            WebviewPlayer.createOrShow(context.extensionUri);
        } catch (e) {
            vscode_1.default.window.showErrorMessage(`Live Wallpaper Player error: ${e.message}`);
        }
    }));
    /** Extract & Apply Dynamic Colors Now */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.extractNow', async () => {
        try {
            if (wallpaper.colorEngine) {
                if (typeof wallpaper.colorEngine.extractCurrentColors === 'function') {
                    await wallpaper.colorEngine.extractCurrentColors();
                } else if (typeof wallpaper.colorEngine.forceExtractNow === 'function') {
                    await wallpaper.colorEngine.forceExtractNow();
                }
                vscode_1.default.window.showInformationMessage('Live Wallpaper: Dynamic colors extracted and synchronized!');
            }
        } catch (e) {
            vscode_1.default.window.showErrorMessage(`Live Wallpaper extract error: ${e.message}`);
        }
    }));
    /** Toggle Dynamic Colors */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.toggleDynamicColors', async () => {
        const cfg = vscode_1.default.workspace.getConfiguration('liveWallpaper.colors');
        const current = cfg.get('enabled', true);
        await cfg.update('enabled', !current, vscode_1.default.ConfigurationTarget.Global);
        vscode_1.default.window.showInformationMessage(`Live Wallpaper: Dynamic colors ${!current ? 'enabled' : 'disabled'}.`);
    }));
    /** Clear Dynamic Colors */
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.clearDynamicColors', async () => {
        try {
            if (wallpaper.colorEngine && wallpaper.colorEngine.themeSync) {
                await wallpaper.colorEngine.themeSync.clearColorCustomizations();
                vscode_1.default.window.showInformationMessage('Live Wallpaper: Dynamic colors cleared.');
            }
        } catch (e) {
            vscode_1.default.window.showErrorMessage(`Live Wallpaper clear error: ${e.message}`);
        }
    }));
    // ── Shared State & Multi-Desktop Synchronization Helpers ──
    const home = process.env.HOME || (process.env.USER ? (fs.existsSync('/var/home/' + process.env.USER) ? '/var/home/' + process.env.USER : '/home/' + process.env.USER) : '');
    const findProjectDir = () => {
        if (process.env.WALLPAPERMAISON_DIR && fs.existsSync(process.env.WALLPAPERMAISON_DIR)) {
            return process.env.WALLPAPERMAISON_DIR;
        }
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
    };
    const stateFile = path.join(home, '.config/wallpapermaison/current_wallpaper.json');

    const stageMediaForWorkbench = (filePath) => new Promise((resolve) => {
        const projectDir = findProjectDir();
        const stageScript = projectDir ? path.join(projectDir, 'app/automation/vscode_media.py') : '';
        if (!stageScript || !fs.existsSync(stageScript)) {
            resolve(filePath);
            return;
        }
        const childProcess = require('child_process');
        childProcess.execFile('python3', [stageScript, filePath, context.extensionPath, '--url'], { timeout: 180000 }, (error, stdout, stderr) => {
            const stagedPath = (stdout || '').trim();
            if (error || !stagedPath) {
                console.warn('[WallpaperMaison] Impossible de préparer le média pour le workbench:', (stderr || '').trim() || error?.message);
                resolve(filePath);
                return;
            }
            resolve(stagedPath);
        });
    });

    const atomicWriteFile = (filePath, content) => {
        const tempPath = `${filePath}.${process.pid}.${Math.random().toString(16).slice(2)}.tmp`;
        try {
            fs.writeFileSync(tempPath, content, 'utf8');
            fs.renameSync(tempPath, filePath);
        } finally {
            try { fs.rmSync(tempPath, { force: true }); } catch (e) {}
        }
    };

    const updateLiveStateFiles = (filePath, mediaType = 'video') => {
        const isVid = mediaType === 'video' || ['.mp4', '.webm', '.mkv', '.mov'].some(ext => filePath.toLowerCase().endsWith(ext));
        const resolvedType = isVid ? 'video' : 'image';
        const st = { path: filePath, media_type: resolvedType, source: 'vscode', timestamp: Date.now() / 1000 };
        const jsonContent = JSON.stringify(st, null, 2);
        const jsContent = `;(function() {
    var p = ${JSON.stringify(filePath)};
    if (typeof window.__applyWallpaperMaisonMedia === 'function') {
        window.__applyWallpaperMaisonMedia(p);
    }
})();\n`;
        const dirs = [
            '/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0',
            path.join(home, '.vscode/extensions/budicuy.live-wallpaper-99.0.0'),
            path.join(home, 'reseau/Perso/.vscode/extensions/budicuy.live-wallpaper-99.0.0'),
            path.join(home, '.config/wallpapermaison'),
            path.join(home, 'reseau/Perso/.config/wallpapermaison')
        ];
        for (const d of dirs) {
            try {
                if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
                atomicWriteFile(path.join(d, 'live_state.json'), jsonContent);
                atomicWriteFile(path.join(d, 'live_state.js'), jsContent);
            } catch (e) {}
        }
    };

    const updateStateAndApply = async (filePath, mediaType = 'video') => {
        try {
            const isVid = mediaType === 'video' || ['.mp4', '.webm', '.mkv', '.mov'].some(ext => filePath.toLowerCase().endsWith(ext));
            const resolvedType = isVid ? 'video' : 'image';

            // 0. Résolution de la version optimisée 1080p pour fluidité maximale sans saccade
            let playablePath = filePath;
            if (isVid) {
                const optCandidates = [
                    path.join(home, '.cache/wallpapermaison/optimized', path.basename(filePath)),
                    path.join(home, 'reseau/Perso/.cache/wallpapermaison/optimized', path.basename(filePath))
                ];
                for (const c of optCandidates) {
                    if (fs.existsSync(c)) {
                        playablePath = c;
                        break;
                    }
                }
            }
            const workbenchPath = await stageMediaForWorkbench(isVid ? playablePath : filePath);

            // 1. Écriture dans le fichier d'état partagé current_wallpaper.json et live_state
            const dir = path.dirname(stateFile);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            const state = {
                path: filePath,
                playable_path: playablePath,
                vscode_path: workbenchPath,
                media_type: resolvedType,
                source: 'vscode',
                timestamp: Date.now() / 1000
            };
            atomicWriteFile(stateFile, JSON.stringify(state, null, 2));
            updateLiveStateFiles(workbenchPath, resolvedType);

            // 2. Application immédiate sur GNOME Shell Mutter (Extension Hanabi ou GSettings Background)
            try {
                const cp = require('child_process');
                if (isVid) {
                    cp.spawn('gsettings', ['set', 'io.github.jeffshee.hanabi-extension', 'video-path', playablePath]);
                    cp.spawn('gdbus', ['call', '--session', '--dest', 'io.github.jeffshee.HanabiRenderer', '--object-path', '/io/github/jeffshee/HanabiRenderer', '--method', 'io.github.jeffshee.HanabiRenderer.setFilePath', playablePath]);
                } else {
                    const fileUri = pathToFileURL(filePath).href;
                    cp.spawn('gsettings', ['set', 'org.gnome.desktop.background', 'picture-uri', fileUri]);
                    cp.spawn('gsettings', ['set', 'org.gnome.desktop.background', 'picture-uri-dark', fileUri]);
                }
            } catch (e) {}

            // 3. Mise à jour de la configuration de l'extension
            await wallpaper.updateConfig({ videoPath: playablePath, enabled: true });

            // 4. Mise à jour synchrone du patch workbench.html
            const projectDir = findProjectDir();
            const patchScript = projectDir ? path.join(projectDir, 'scripts/patch_vscode_html.py') : '';
            if (patchScript && fs.existsSync(patchScript)) {
                try {
                    require('child_process').spawnSync('python3', [patchScript, playablePath], { timeout: 30000 });
                } catch (e) {}
            }

            // 5. Extraction dynamique des couleurs si activée
            if (wallpaper.colorEngine) {
                try {
                    if (typeof wallpaper.colorEngine.extractCurrentColors === 'function') {
                        wallpaper.colorEngine.extractCurrentColors().catch(() => {});
                    } else if (typeof wallpaper.colorEngine.forceExtractNow === 'function') {
                        wallpaper.colorEngine.forceExtractNow().catch(() => {});
                    }
                } catch (e) {}
            }

            // 6. Notification
            vscode_1.default.window.setStatusBarMessage(`🖼️ Fond d'écran appliqué : ${path.basename(filePath)}`, 4000);
        } catch (err) {
            vscode_1.default.window.showErrorMessage(`Erreur application fond d'écran : ${err.message}`);
        }
    };

    // ── Rotation Manager Initialization ──
    const { RotationManager } = require('./rotationManager');
    const rotationManager = new RotationManager(async (filePath, mediaType) => {
        await updateStateAndApply(filePath, mediaType);
    });
    rotationManager.loadSettings();

    // ── Rotation Commands ──
    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.toggleRotation', async () => {
        const state = rotationManager.saveSettings({ enabled: !rotationManager.settings.enabled });
        vscode_1.default.window.showInformationMessage(`Live Wallpaper: Rotation automatique ${state.enabled ? 'activée (' + state.intervalMinutes + ' min)' : 'désactivée'}.`);
    }));

    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.nextWallpaper', async () => {
        const next = await rotationManager.nextWallpaper();
        if (next) {
            vscode_1.default.window.showInformationMessage(`⏭️ Fond d'écran suivant : ${path.basename(next)}`);
        }
    }));

    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.chooseRotationFolder', async () => {
        const uris = await vscode_1.default.window.showOpenDialog({
            canSelectFiles: false,
            canSelectFolders: true,
            canSelectMany: false,
            title: 'Sélectionner le dossier pour la rotation automatique'
        });
        if (uris && uris.length > 0) {
            const folder = uris[0].fsPath;
            rotationManager.saveSettings({ folder: folder });
            const stats = rotationManager.getStats(folder);
            vscode_1.default.window.showInformationMessage(`Dossier de rotation configuré : ${folder} (${stats.total} médias détectés)`);
        }
    }));

    // ── Choose Wallpaper Integration (Button & Command) ──
    const wpStatusBar = vscode_1.default.window.createStatusBarItem('chooseWallpaperStatusItem', vscode_1.default.StatusBarAlignment.Right, 101);
    wpStatusBar.name = 'Choisir Wallpaper';
    wpStatusBar.command = 'liveWallpaper.chooseWallpaper';
    wpStatusBar.text = '$(file-media) Wallpaper';
    wpStatusBar.tooltip = '🖼️ Choisir un nouveau Wallpaper (Synchronisé Bureau & VS Code)';
    wpStatusBar.show();
    context.subscriptions.push(wpStatusBar);

    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.chooseWallpaper', async () => {
        const choice = await vscode_1.default.window.showQuickPick([
            {
                label: '$(folder) Parcourir les fichiers (Vidéo / Image)...',
                description: 'Sélectionner un fichier local MP4, WebM, PNG, JPG...',
                action: 'file'
            },
            {
                label: '$(sync) Rotation automatique (Activer / Suivant)...',
                description: `Statut : ${rotationManager.settings.enabled ? 'Actif (' + rotationManager.settings.intervalMinutes + 'm)' : 'Désactivé'} - Dossier : ${path.basename(rotationManager.settings.folder)}`,
                action: 'rotation'
            },
            {
                label: '$(globe) Entrer une URL / Lien direct...',
                description: 'Télécharger et appliquer depuis un lien HTTP/HTTPS',
                action: 'url'
            },
            {
                label: '$(sync) Synchroniser avec le fond d\'écran du bureau',
                description: 'Détecter et réappliquer le fond d\'écran actif du bureau',
                action: 'sync'
            }
        ], {
            placeHolder: '🖼️ Choisir un nouveau fond d\'écran (Bureau & VS Code)'
        });

        if (!choice) return;

        if (choice.action === 'file') {
            const uris = await vscode_1.default.window.showOpenDialog({
                canSelectFiles: true,
                canSelectFolders: false,
                canSelectMany: false,
                title: 'Sélectionner un nouveau fond d\'écran',
                filters: {
                    'Vidéos et Images': ['mp4', 'webm', 'mkv', 'mov', 'png', 'jpg', 'jpeg', 'webp', 'gif'],
                    'Vidéos': ['mp4', 'webm', 'mkv', 'mov'],
                    'Images': ['png', 'jpg', 'jpeg', 'webp', 'gif'],
                    'Tous les fichiers': ['*']
                }
            });
            if (uris && uris.length > 0) {
                const selected = uris[0].fsPath;
                const isVideo = ['.mp4', '.webm', '.mkv', '.mov'].some(ext => selected.toLowerCase().endsWith(ext));
                await updateStateAndApply(selected, isVideo ? 'video' : 'image');
            }
        } else if (choice.action === 'url') {
            const url = await vscode_1.default.window.showInputBox({
                prompt: 'Entrez l\'URL directe de la vidéo ou de l\'image (HTTP/HTTPS)',
                placeHolder: 'https://example.com/wallpaper.mp4',
                validateInput: (text) => {
                    if (!text || (!text.startsWith('http://') && !text.startsWith('https://'))) {
                        return 'Veuillez renseigner une URL valide commençant par http:// ou https://';
                    }
                    return null;
                }
            });
            if (url) {
                vscode_1.default.window.withProgress({
                    location: vscode_1.default.ProgressLocation.Notification,
                    title: 'Téléchargement du fond d\'écran...',
                    cancellable: false
                }, async () => {
                    try {
                        const dlDir = path.join(home, '.local/share/wallpapermaison/downloads');
                        if (!fs.existsSync(dlDir)) fs.mkdirSync(dlDir, { recursive: true });
                        const parsedUrl = new URL(url);
                        let filename = path.basename(parsedUrl.pathname) || 'wallpaper.mp4';
                        if (!path.extname(filename)) filename += '.mp4';
                        const hash = require('crypto').createHash('md5').update(url).digest('hex').slice(0, 8);
                        const destPath = path.join(dlDir, `${hash}_${filename}`);

                        await new Promise((resolve, reject) => {
                            const cp = require('child_process').spawn('curl', ['-sL', '-o', destPath, url]);
                            cp.on('close', code => code === 0 ? resolve() : reject(new Error(`curl code ${code}`)));
                            cp.on('error', reject);
                        });

                        if (fs.existsSync(destPath) && fs.statSync(destPath).size > 0) {
                            const isVideo = ['.mp4', '.webm', '.mkv', '.mov'].some(ext => destPath.toLowerCase().endsWith(ext));
                            await updateStateAndApply(destPath, isVideo ? 'video' : 'image');
                        } else {
                            throw new Error('Fichier téléchargé vide ou inexistant.');
                        }
                    } catch (e) {
                        vscode_1.default.window.showErrorMessage(`Échec du téléchargement : ${e.message}`);
                    }
                });
            }
        } else if (choice.action === 'sync') {
            const { WallpaperBridge } = require('./colors/wallpaperBridge');
            const cur = WallpaperBridge.detectCurrentWallpaper();
            if (cur && fs.existsSync(cur)) {
                const isVideo = ['.mp4', '.webm', '.mkv', '.mov'].some(ext => cur.toLowerCase().endsWith(ext));
                await updateStateAndApply(cur, isVideo ? 'video' : 'image');
            } else {
                vscode_1.default.window.showWarningMessage('Aucun fond d\'écran actif détecté sur le bureau.');
            }
        }
    }));

    // Surveillance continue pour synchroniser automatiquement VS Code si le Bureau change
    try {
        const homeDir = home;
        const stateFilePath = path.join(homeDir, '.config/wallpapermaison/current_wallpaper.json');
        let lastSeenTimestamp = 0;
        const syncInterval = setInterval(() => {
            try {
                let currentDetected = null;
                if (fs.existsSync(stateFilePath)) {
                    const raw = fs.readFileSync(stateFilePath, 'utf8');
                    const data = JSON.parse(raw);
                    if (data && data.path) {
                        currentDetected = data.playable_path && fs.existsSync(data.playable_path)
                            ? data.playable_path
                            : data.path;
                    }
                }
                if (!currentDetected) {
                    const { WallpaperBridge } = require('./colors/wallpaperBridge');
                    currentDetected = WallpaperBridge.detectCurrentWallpaper();
                }
                if (!currentDetected) {
                    const proj = findProjectDir();
                    if (proj) {
                        const wpDir = path.join(proj, 'Wallpaper');
                        if (fs.existsSync(wpDir)) {
                            try {
                                const files = fs.readdirSync(wpDir).filter(f => ['.mp4', '.webm'].some(ext => f.toLowerCase().endsWith(ext)));
                                if (files.length > 0) {
                                    currentDetected = path.join(wpDir, files[0]);
                                }
                            } catch (e) {}
                        }
                    }
                }
                if (currentDetected && fs.existsSync(currentDetected)) {
                    const curCfg = wallpaper.getRawConfig();
                    const samePath = (a, b) => {
                        try {
                            return fs.realpathSync(a) === fs.realpathSync(b);
                        } catch (e) {
                            return path.resolve(a || '') === path.resolve(b || '');
                        }
                    };
                    if (!samePath(curCfg.videoPath, currentDetected)) {
                        wallpaper.updateConfig({ videoPath: currentDetected, enabled: true }).catch(() => {});
                        const projectDir = findProjectDir();
                        const patchScript = projectDir ? path.join(projectDir, 'scripts/patch_vscode_html.py') : '';
                        if (patchScript && fs.existsSync(patchScript)) {
                            try {
                                require('child_process').spawnSync('python3', [patchScript, currentDetected], { timeout: 30000 });
                            } catch (e) {}
                        }
                        if (wallpaper.colorEngine) {
                            try {
                                if (typeof wallpaper.colorEngine.extractCurrentColors === 'function') {
                                    wallpaper.colorEngine.extractCurrentColors().catch(() => {});
                                } else if (typeof wallpaper.colorEngine.forceExtractNow === 'function') {
                                    wallpaper.colorEngine.forceExtractNow().catch(() => {});
                                }
                            } catch (e) {}
                        }
                        vscode_1.default.window.setStatusBarMessage(`🖼️ Fond d'écran synchronisé : ${path.basename(currentDetected)}`, 4000);
                    }
                }
            } catch (err) {}
        }, 1000);
        context.subscriptions.push({ dispose: () => clearInterval(syncInterval) });
    } catch (e) {}

    // ── Sudo Root Terminal Integration ──
    function getRootShell() {
        const user = process.env.USER || '';
        const candidates = [
            path.join(home, '.local/bin/root-shell'),
            path.join(home, 'reseau/Perso/.local/bin/root-shell'),
            user ? `/var/home/${user}/.local/bin/root-shell` : '',
            user ? `/home/${user}/.local/bin/root-shell` : '',
            'root-shell'
        ];
        for (const c of candidates) {
            if (c && (c === 'root-shell' || fs.existsSync(c))) {
                return c;
            }
        }
        return 'root-shell';
    }

    const sudoStatusBar = vscode_1.default.window.createStatusBarItem('sudoRootStatusItem', vscode_1.default.StatusBarAlignment.Left, 10000);
    sudoStatusBar.name = '⚡ Sudo Root';
    sudoStatusBar.command = 'liveWallpaper.openSudoTerminal';
    sudoStatusBar.text = '$(shield) ⚡ Sudo Root';
    sudoStatusBar.tooltip = '⚡ Ouvrir un Terminal Administrateur Root Séparé (Sans mot de passe)';
    sudoStatusBar.show();
    context.subscriptions.push(sudoStatusBar);

    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.openSudoTerminal', () => {
        const rootShell = getRootShell();
        const term = vscode_1.default.window.createTerminal({
            name: '⚡ Sudo Root',
            shellPath: rootShell,
            iconPath: new vscode_1.default.ThemeIcon('shield'),
            color: new vscode_1.default.ThemeColor('terminal.ansiRed')
        });
        term.show();
    }));

    context.subscriptions.push(vscode_1.default.commands.registerCommand('liveWallpaper.splitSudoTerminal', () => {
        const rootShell = getRootShell();
        const term = vscode_1.default.window.createTerminal({
            name: '⚡ Sudo Root (Split)',
            shellPath: rootShell,
            location: vscode_1.default.TerminalLocation.Panel,
            iconPath: new vscode_1.default.ThemeIcon('shield'),
            color: new vscode_1.default.ThemeColor('terminal.ansiRed')
        });
        term.show();
    }));

    try {
        context.subscriptions.push(vscode_1.default.window.registerWebviewViewProvider('wallpaper-view', {
            resolveWebviewView(webviewView) {
                webviewView.webview.options = { enableScripts: true };

                const getCurrentPath = () => {
                    const sf = path.join(home, '.config/wallpapermaison/current_wallpaper.json');
                    try {
                        if (fs.existsSync(sf)) {
                            const d = JSON.parse(fs.readFileSync(sf, 'utf8'));
                            return d.path || '';
                        }
                    } catch {}
                    return '';
                };

                const sendFullState = () => {
                    try {
                        const cur = getCurrentPath();
                        const st = rotationManager.getState();
                        const isVid = ['.mp4', '.webm', '.mkv', '.mov'].some(ext => cur.toLowerCase().endsWith(ext));
                        webviewView.webview.postMessage({
                            type: 'fullState',
                            path: cur,
                            basename: path.basename(cur),
                            isVideo: isVid,
                            ...st
                        });
                    } catch (e) {}
                };

                const getHtml = (currentPath, rotState) => {
                    const isVid = ['.mp4', '.webm', '.mkv', '.mov'].some(ext => currentPath.toLowerCase().endsWith(ext));
                    const base = path.basename(currentPath) || 'Aucun fond sélectionné';
                    const proj = findProjectDir();
                    const pProjectWallpapers = proj ? path.join(proj, 'Wallpaper') : '';
                    const pDownloads = fs.existsSync(path.join(home, 'reseau/Perso/Téléchargements'))
                        ? path.join(home, 'reseau/Perso/Téléchargements')
                        : path.join(home, 'Downloads');
                    const pWallpapers = fs.existsSync(path.join(home, 'reseau/Perso/Images/Wallpapers'))
                        ? path.join(home, 'reseau/Perso/Images/Wallpapers')
                        : path.join(home, 'Pictures/Wallpapers');

                    return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
    :root {
        --accent: #38bdf8;
        --accent-gradient: linear-gradient(135deg, #0284c7, #2563eb);
        --accent-glow: rgba(56, 189, 248, 0.35);
        --card-bg: rgba(255, 255, 255, 0.04);
        --card-border: rgba(255, 255, 255, 0.08);
        --success: #10b981;
        --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        padding: 12px 10px;
        font-family: var(--vscode-font-family, system-ui, sans-serif);
        font-size: 12px;
        color: var(--vscode-foreground, #e5edf2);
        background: transparent;
        line-height: 1.4;
        overflow-x: hidden;
    }
    .app-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--card-border);
    }
    .app-icon { font-size: 18px; }
    .app-title-group h2 {
        font-size: 13px;
        font-weight: 700;
        background: linear-gradient(135deg, #e0f2fe, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .app-subtitle { font-size: 10px; color: var(--text-muted); }
    .card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 9px;
        padding: 10px 12px;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        transition: border-color 0.2s ease;
    }
    .card:hover { border-color: rgba(56, 189, 248, 0.25); }
    .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .card-title {
        font-size: 11.5px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
        color: #f1f5f9;
    }
    .badge {
        padding: 2px 7px;
        border-radius: 5px;
        font-size: 10px;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-cyan {
        background: rgba(56, 189, 248, 0.14);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #7dd3fc;
    }
    .cur-box {
        background: rgba(0, 0, 0, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 7px;
        padding: 8px 10px;
    }
    .cur-name {
        font-size: 12px;
        font-weight: 600;
        color: #f8fafc;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 3px;
    }
    .cur-path {
        font-size: 10px;
        font-family: monospace;
        color: var(--text-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        background: rgba(255, 255, 255, 0.03);
        padding: 2px 5px;
        border-radius: 4px;
    }
    /* Toggle Switch */
    .switch {
        position: relative;
        display: inline-block;
        width: 40px;
        height: 22px;
        flex-shrink: 0;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
        position: absolute;
        cursor: pointer;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: rgba(255, 255, 255, 0.15);
        border-radius: 22px;
        transition: 0.25s;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 2px;
        bottom: 2px;
        background-color: white;
        border-radius: 50%;
        transition: 0.25s;
    }
    input:checked + .slider {
        background: #0284c7;
        box-shadow: 0 0 10px rgba(2, 132, 199, 0.6);
        border-color: #38bdf8;
    }
    input:checked + .slider:before {
        transform: translateX(18px);
    }
    /* Status banner */
    .status-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(0, 0, 0, 0.25);
        padding: 7px 10px;
        border-radius: 6px;
        margin: 8px 0;
        border-left: 3px solid #64748b;
        font-size: 11px;
    }
    .status-banner.active {
        border-left-color: var(--success);
        background: rgba(16, 185, 129, 0.08);
    }
    .pulse-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #64748b;
        display: inline-block;
        margin-right: 5px;
    }
    .status-banner.active .pulse-dot {
        background: var(--success);
        box-shadow: 0 0 7px var(--success);
        animation: pulse 1.6s infinite ease-in-out;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.35); opacity: 0.7; }
    }
    .countdown-val {
        font-family: monospace;
        font-weight: 700;
        color: #38bdf8;
        font-size: 12.5px;
    }
    /* Fields */
    .field-label {
        font-size: 10.5px;
        font-weight: 600;
        color: #cbd5e1;
        margin: 8px 0 4px 0;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .folder-display {
        font-family: monospace;
        font-size: 10px;
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 5px;
        padding: 5px 8px;
        color: #93c5fd;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 6px;
    }
    .chips-group {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin: 5px 0;
    }
    .chip {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #94a3b8;
        font-size: 9.5px;
        padding: 2px 6px;
        border-radius: 4px;
    }
    .preset-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.09);
        color: #cbd5e1;
        padding: 3px 7px;
        border-radius: 4px;
        font-size: 10px;
        cursor: pointer;
        transition: all 0.15s;
    }
    .preset-btn:hover, .preset-btn.active {
        background: rgba(56, 189, 248, 0.18);
        border-color: #38bdf8;
        color: #7dd3fc;
    }
    /* Stepper */
    .interval-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    .stepper {
        display: flex;
        align-items: center;
        background: rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 6px;
        overflow: hidden;
    }
    .btn-step {
        background: rgba(255, 255, 255, 0.08);
        border: none;
        color: #f8fafc;
        width: 28px;
        height: 28px;
        cursor: pointer;
        font-size: 15px;
        font-weight: bold;
        transition: background 0.15s;
    }
    .btn-step:hover { background: rgba(56, 189, 248, 0.25); }
    .interval-input {
        width: 44px;
        height: 28px;
        background: transparent;
        border: none;
        text-align: center;
        color: #38bdf8;
        font-weight: 700;
        font-size: 12px;
        font-family: monospace;
    }
    .interval-input:focus { outline: none; }
    /* Segmented Control */
    .segmented {
        display: flex;
        background: rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        padding: 2px;
        gap: 2px;
        margin: 5px 0 8px 0;
    }
    .seg-btn {
        flex: 1;
        padding: 5px 8px;
        border: none;
        border-radius: 5px;
        background: transparent;
        color: #94a3b8;
        font-size: 10.5px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    .seg-btn.active {
        background: var(--accent-gradient);
        color: white;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.4);
    }
    /* Buttons */
    .btn-action {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        width: 100%;
        padding: 8px 12px;
        margin-top: 6px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 11px;
        font-weight: 600;
        transition: all 0.15s ease;
        border: none;
    }
    .btn-primary {
        background: var(--accent-gradient);
        color: white;
        border: 1px solid rgba(56, 189, 248, 0.4);
        box-shadow: 0 3px 10px var(--accent-glow);
    }
    .btn-primary:hover {
        filter: brightness(1.15);
        transform: translateY(-1px);
    }
    .btn-outline {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #e2e8f0;
    }
    .btn-outline:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.25);
    }
    .btn-next {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        border: 1px solid #34d399;
        box-shadow: 0 3px 10px rgba(16, 185, 129, 0.3);
    }
    .btn-next:hover {
        filter: brightness(1.15);
        transform: translateY(-1px);
    }
    .save-feedback {
        display: none;
        font-size: 10.5px;
        color: #34d399;
        text-align: center;
        margin-top: 5px;
        font-weight: 600;
    }
</style>
</head>
<body>
    <div class="app-header">
        <div class="app-icon">🌌</div>
        <div class="app-title-group">
            <h2>WallpaperMaison</h2>
            <div class="app-subtitle">Mutter &bull; VS Code &bull; Multi-Postes</div>
        </div>
    </div>

    <!-- 1. Fond d'Écran Actif -->
    <div class="card">
        <div class="card-header">
            <div class="card-title">🖼️ Fond d'Écran Actuel</div>
            <div class="badge badge-cyan" id="curTypeBadge">${isVid ? '🎬 Vidéo 4K' : '🖼️ Image'}</div>
        </div>
        <div class="cur-box">
            <div class="cur-name" id="curNameDisplay">${base}</div>
            <div class="cur-path" id="curPathDisplay">${currentPath || 'Aucun média actif'}</div>
        </div>
    </div>

    <!-- 2. Rotation Automatique (Slideshow) -->
    <div class="card">
        <div class="card-header">
            <div class="card-title">⏱️ Rotation Automatique</div>
            <label class="switch" title="Activer ou désactiver le changement automatique">
                <input type="checkbox" id="rotToggle" ${rotState.enabled ? 'checked' : ''}>
                <span class="slider"></span>
            </label>
        </div>

        <div class="status-banner ${rotState.enabled ? 'active' : ''}" id="statusBanner">
            <div>
                <span class="pulse-dot"></span>
                <span id="statusText">${rotState.enabled ? 'En cours &bull; Prochain dans' : 'Rotation en pause'}</span>
            </div>
            <div class="countdown-val" id="countdownVal">${rotState.enabled ? rotState.timeRemainingFormatted : '--:--'}</div>
        </div>

        <div class="field-label">📁 Dossier source des wallpapers :</div>
        <div class="folder-display" id="folderDisplay" title="${rotState.folder}">${rotState.folder}</div>

        <div style="display: flex; gap: 5px; margin-bottom: 6px;">
            <button class="btn-action btn-outline" id="btnBrowseFolder" style="margin-top:0; padding: 6px 10px;">
                📂 Parcourir un dossier...
            </button>
        </div>

        <div class="chips-group">
            ${pProjectWallpapers ? `<button class="preset-btn" id="btnPresetProject" title="${pProjectWallpapers}">🌌 Wallpapers Dépôt</button>` : ''}
            <button class="preset-btn" id="btnPresetDownloads" title="${pDownloads}">🎬 Téléchargements</button>
            <button class="preset-btn" id="btnPresetWallpapers" title="${pWallpapers}">🖼️ Images HD</button>
            <span class="chip">🎬 <span id="videoCount">${rotState.videoCount}</span> vid</span>
            <span class="chip">🖼️ <span id="imageCount">${rotState.imageCount}</span> img</span>
            <span class="chip">Total: <span id="totalCount">${rotState.totalCount}</span></span>
        </div>

        <div class="field-label">⏳ Intervalle de changement :</div>
        <div class="interval-row">
            <div class="stepper">
                <button class="btn-step" id="btnStepMinus">-</button>
                <input type="number" class="interval-input" id="intervalInput" min="1" max="1440" value="${rotState.intervalMinutes}">
                <button class="btn-step" id="btnStepPlus">+</button>
            </div>
            <span style="font-size: 11px; color: #cbd5e1; font-weight: 600;">minutes</span>
        </div>

        <div class="chips-group" id="intervalPresets">
            <button class="preset-btn ${rotState.intervalMinutes === 1 ? 'active' : ''}" data-min="1">1 min</button>
            <button class="preset-btn ${rotState.intervalMinutes === 3 ? 'active' : ''}" data-min="3">3 min</button>
            <button class="preset-btn ${rotState.intervalMinutes === 5 ? 'active' : ''}" data-min="5">5 min</button>
            <button class="preset-btn ${rotState.intervalMinutes === 10 ? 'active' : ''}" data-min="10">10 min</button>
            <button class="preset-btn ${rotState.intervalMinutes === 15 ? 'active' : ''}" data-min="15">15 min</button>
            <button class="preset-btn ${rotState.intervalMinutes === 30 ? 'active' : ''}" data-min="30">30 min</button>
            <button class="preset-btn ${rotState.intervalMinutes === 60 ? 'active' : ''}" data-min="60">60 min</button>
        </div>

        <div class="field-label">🔀 Ordre de sélection :</div>
        <div class="segmented">
            <button class="seg-btn ${rotState.order === 'random' ? 'active' : ''}" id="segRandom">🎲 Aléatoire</button>
            <button class="seg-btn ${rotState.order === 'sequential' ? 'active' : ''}" id="segSequential">🔁 Dans l'ordre</button>
        </div>

        <button class="btn-action btn-next" id="btnNext">
            ⏭️ Passer au suivant immédiatement
        </button>

        <button class="btn-action btn-outline" id="btnSaveConfig" style="margin-top: 6px;">
            💾 Enregistrer dans les réglages (.env & JSON)
        </button>
        <div class="save-feedback" id="saveFeedback">✓ Paramètres enregistrés et persistés !</div>
    </div>

    <!-- 3. Actions Rapides -->
    <div class="card">
        <div class="card-title" style="margin-bottom: 8px;">⚡ Actions Rapides</div>
        <button class="btn-action btn-primary" id="btnChooseFile">
            📁 Choisir un fichier manuellement...
        </button>
        <button class="btn-action btn-outline" id="btnChooseUrl">
            🌐 Télécharger depuis un lien URL...
        </button>
        <button class="btn-action btn-outline" id="btnSyncDesktop">
            🔄 Forcer la synchronisation Bureau &harr; VS Code
        </button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        const rotToggle = document.getElementById('rotToggle');
        const statusBanner = document.getElementById('statusBanner');
        const statusText = document.getElementById('statusText');
        const countdownVal = document.getElementById('countdownVal');
        const folderDisplay = document.getElementById('folderDisplay');
        const intervalInput = document.getElementById('intervalInput');
        const segRandom = document.getElementById('segRandom');
        const segSequential = document.getElementById('segSequential');
        const videoCount = document.getElementById('videoCount');
        const imageCount = document.getElementById('imageCount');
        const totalCount = document.getElementById('totalCount');
        const saveFeedback = document.getElementById('saveFeedback');
        const curNameDisplay = document.getElementById('curNameDisplay');
        const curPathDisplay = document.getElementById('curPathDisplay');
        const curTypeBadge = document.getElementById('curTypeBadge');

        let currentOrder = '${rotState.order}';

        function showSaved() {
            saveFeedback.style.display = 'block';
            setTimeout(() => { saveFeedback.style.display = 'none'; }, 2200);
        }

        // Toggle rotation
        rotToggle.addEventListener('change', () => {
            const enabled = rotToggle.checked;
            statusBanner.classList.toggle('active', enabled);
            statusText.textContent = enabled ? 'En cours • Prochain dans' : 'Rotation en pause';
            if (!enabled) countdownVal.textContent = '--:--';
            vscode.postMessage({ command: 'toggleRotation', enabled: enabled });
            showSaved();
        });

        // Stepper interval
        document.getElementById('btnStepMinus').onclick = () => {
            let v = Math.max(1, parseInt(intervalInput.value || 5, 10) - 1);
            intervalInput.value = v;
            updateInterval(v);
        };
        document.getElementById('btnStepPlus').onclick = () => {
            let v = parseInt(intervalInput.value || 5, 10) + 1;
            intervalInput.value = v;
            updateInterval(v);
        };
        intervalInput.onchange = () => {
            let v = Math.max(1, parseInt(intervalInput.value || 5, 10));
            intervalInput.value = v;
            updateInterval(v);
        };

        function updateInterval(mins) {
            document.querySelectorAll('#intervalPresets .preset-btn').forEach(b => {
                b.classList.toggle('active', parseInt(b.dataset.min, 10) === mins);
            });
            vscode.postMessage({ command: 'setInterval', intervalMinutes: mins });
            showSaved();
        }

        // Presets interval
        document.querySelectorAll('#intervalPresets .preset-btn').forEach(btn => {
            btn.onclick = () => {
                const m = parseInt(btn.dataset.min, 10);
                intervalInput.value = m;
                updateInterval(m);
            };
        });

        // Segmented order
        segRandom.onclick = () => {
            currentOrder = 'random';
            segRandom.classList.add('active');
            segSequential.classList.remove('active');
            vscode.postMessage({ command: 'setOrder', order: 'random' });
            showSaved();
        };
        segSequential.onclick = () => {
            currentOrder = 'sequential';
            segSequential.classList.add('active');
            segRandom.classList.remove('active');
            vscode.postMessage({ command: 'setOrder', order: 'sequential' });
            showSaved();
        };

        // Browse folder
        document.getElementById('btnBrowseFolder').onclick = () => {
            vscode.postMessage({ command: 'chooseFolder' });
        };
        const btnProject = document.getElementById('btnPresetProject');
        if (btnProject) {
            btnProject.onclick = () => {
                vscode.postMessage({ command: 'setFolder', folder: '${pProjectWallpapers}' });
                showSaved();
            };
        }
        document.getElementById('btnPresetDownloads').onclick = () => {
            vscode.postMessage({ command: 'setFolder', folder: '${pDownloads}' });
            showSaved();
        };
        document.getElementById('btnPresetWallpapers').onclick = () => {
            vscode.postMessage({ command: 'setFolder', folder: '${pWallpapers}' });
            showSaved();
        };

        // Next wallpaper
        document.getElementById('btnNext').onclick = () => {
            vscode.postMessage({ command: 'nextWallpaper' });
        };

        // Save
        document.getElementById('btnSaveConfig').onclick = () => {
            vscode.postMessage({
                command: 'saveSettings',
                settings: {
                    enabled: rotToggle.checked,
                    intervalMinutes: parseInt(intervalInput.value || 5, 10),
                    order: currentOrder
                }
            });
            showSaved();
        };

        // Quick actions
        document.getElementById('btnChooseFile').onclick = () => vscode.postMessage({ command: 'chooseFile' });
        document.getElementById('btnChooseUrl').onclick = () => vscode.postMessage({ command: 'chooseUrl' });
        document.getElementById('btnSyncDesktop').onclick = () => vscode.postMessage({ command: 'syncDesktop' });

        // Listen for messages from extension host
        window.addEventListener('message', e => {
            const data = e.data;
            if (!data) return;

            if (data.type === 'fullState' || data.type === 'tick') {
                if (data.basename) curNameDisplay.textContent = data.basename;
                if (data.path) {
                    curPathDisplay.textContent = data.path;
                    curTypeBadge.textContent = data.isVideo ? '🎬 Vidéo 4K' : '🖼️ Image';
                }
                if (typeof data.enabled === 'boolean') {
                    rotToggle.checked = data.enabled;
                    statusBanner.classList.toggle('active', data.enabled);
                    statusText.textContent = data.enabled ? 'En cours • Prochain dans' : 'Rotation en pause';
                }
                if (data.timeRemainingFormatted) {
                    countdownVal.textContent = data.enabled ? data.timeRemainingFormatted : '--:--';
                }
                if (data.folder) {
                    folderDisplay.textContent = data.folder;
                    folderDisplay.title = data.folder;
                }
                if (typeof data.totalCount === 'number') totalCount.textContent = data.totalCount;
                if (typeof data.videoCount === 'number') videoCount.textContent = data.videoCount;
                if (typeof data.imageCount === 'number') imageCount.textContent = data.imageCount;
                if (data.order) {
                    currentOrder = data.order;
                    segRandom.classList.toggle('active', data.order === 'random');
                    segSequential.classList.toggle('active', data.order === 'sequential');
                }
                if (data.intervalMinutes) {
                    intervalInput.value = data.intervalMinutes;
                    document.querySelectorAll('#intervalPresets .preset-btn').forEach(b => {
                        b.classList.toggle('active', parseInt(b.dataset.min, 10) === data.intervalMinutes);
                    });
                }
            }
        });
    </script>
</body>
</html>`;
                };

                webviewView.webview.html = getHtml(getCurrentPath(), rotationManager.getState());

                // Communication de l'interface vers l'hôte VS Code
                webviewView.webview.onDidReceiveMessage(async (message) => {
                    if (!message) return;

                    if (message.command === 'chooseFile') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.chooseWallpaper');
                    } else if (message.command === 'chooseUrl') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.chooseWallpaper');
                    } else if (message.command === 'syncDesktop') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.chooseWallpaper');
                    } else if (message.command === 'toggleRotation') {
                        rotationManager.saveSettings({ enabled: !!message.enabled });
                        sendFullState();
                    } else if (message.command === 'setInterval') {
                        rotationManager.saveSettings({ intervalMinutes: Math.max(1, Number(message.intervalMinutes) || 5) });
                        sendFullState();
                    } else if (message.command === 'setOrder') {
                        rotationManager.saveSettings({ order: message.order });
                        sendFullState();
                    } else if (message.command === 'setFolder') {
                        rotationManager.saveSettings({ folder: message.folder });
                        sendFullState();
                    } else if (message.command === 'chooseFolder') {
                        const uris = await vscode_1.default.window.showOpenDialog({
                            canSelectFiles: false,
                            canSelectFolders: true,
                            canSelectMany: false,
                            title: 'Sélectionner le dossier pour la rotation automatique'
                        });
                        if (uris && uris.length > 0) {
                            rotationManager.saveSettings({ folder: uris[0].fsPath });
                            sendFullState();
                        }
                    } else if (message.command === 'nextWallpaper') {
                        await rotationManager.nextWallpaper();
                        sendFullState();
                    } else if (message.command === 'saveSettings') {
                        rotationManager.saveSettings(message.settings || {});
                        sendFullState();
                    }
                });

                // Écouter les notifications de RotationManager
                const onRotationChange = (st) => {
                    sendFullState();
                };
                rotationManager.addListener(onRotationChange);

                // Tick toutes les 1s pour le compte à rebours
                const interval = setInterval(() => {
                    sendFullState();
                }, 1000);

                webviewView.onDidDispose(() => {
                    clearInterval(interval);
                    rotationManager.removeListener(onRotationChange);
                });
            }
        }));
    } catch (e) {
        console.error('Error registering wallpaper-view:', e);
    }

    try {
        context.subscriptions.push(vscode_1.default.window.registerWebviewViewProvider('sudo-root-view', {
            resolveWebviewView(webviewView) {
                vscode_1.default.commands.executeCommand('liveWallpaper.openSudoTerminal');
                webviewView.webview.options = { enableScripts: true };
                webviewView.webview.html = `<!DOCTYPE html><html><body style="padding:16px;font-family:system-ui,sans-serif;color:#e5edf2;background:#16181a;text-align:center;">
                    <div style="background:rgba(239,68,68,0.18);border:1px solid #ef4444;color:#fca5a5;padding:6px 12px;border-radius:6px;font-size:12px;display:inline-block;margin-bottom:12px;font-weight:bold;">⚡ ACCÈS ROOT PRIVILÉGIÉ</div>
                    <h3 style="margin:8px 0;">Terminal Administrateur Sudo</h3>
                    <p style="color:#9aa1a6;font-size:13px;line-height:1.4;">Accès root total sans mot de passe, séparé de votre terminal classique.</p>
                    <button id="btn" style="margin-top:16px;background:linear-gradient(135deg, #ef4444, #b91c1c);color:white;border:1px solid #fca5a5;padding:10px 20px;border-radius:6px;font-weight:bold;cursor:pointer;width:100%;font-size:14px;box-shadow:0 4px 12px rgba(239,68,68,0.4);">⚡ Nouveau Terminal Root Séparé</button>
                    <button id="btnSplit" style="margin-top:8px;background:rgba(255,255,255,0.08);color:#e5edf2;border:1px solid rgba(255,255,255,0.2);padding:8px 16px;border-radius:6px;font-weight:600;cursor:pointer;width:100%;font-size:13px;">⚡ Diviser le Terminal en Root (Split)</button>
                    <script>
                        const vscode = acquireVsCodeApi();
                        document.getElementById('btn').onclick = () => vscode.postMessage({ command: 'newTerminal' });
                        document.getElementById('btnSplit').onclick = () => vscode.postMessage({ command: 'splitTerminal' });
                    </script>
                </body></html>`;
                webviewView.webview.onDidReceiveMessage(message => {
                    if (message && message.command === 'newTerminal') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.openSudoTerminal');
                    } else if (message && message.command === 'splitTerminal') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.splitSudoTerminal');
                    }
                });
            }
        }));
    } catch (e) {
        console.error('Error registering sudo-root-view:', e);
    }
    // ── Setup — runs after commands are registered ─────────────────────────
    // Wrap in try-catch so a setup error never prevents commands from working.
    try {
        await wallpaper.setup();
    }
    catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        vscode_1.default.window.showErrorMessage(`Live Wallpaper: Failed to initialize — ${msg}. ` +
            `You can still use the Apply / Disable commands manually.`);
    }
}
/** Called when the extension is deactivated */
function deactivate() { }
