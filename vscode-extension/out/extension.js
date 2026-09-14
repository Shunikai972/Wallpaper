"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const fs = require('fs');
const path = require('path');
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

        const home = process.env.HOME || '/var/home/' + (process.env.USER || 'E256190S');
        const stateFile = path.join(home, '.config/wallpapermaison/current_wallpaper.json');

        const updateStateAndApply = async (filePath, mediaType = 'video') => {
            try {
                // 1. Écriture dans le fichier d'état partagé current_wallpaper.json
                const dir = path.dirname(stateFile);
                if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                const state = {
                    path: filePath,
                    media_type: mediaType,
                    source: 'vscode',
                    timestamp: Date.now() / 1000
                };
                fs.writeFileSync(stateFile, JSON.stringify(state, null, 2), 'utf8');

                // 2. Mise à jour de la configuration de l'extension
                await wallpaper.updateConfig({ videoPath: filePath, enabled: true });

                // 3. Mise à jour du patch workbench.html
                const patchScript = path.join(home, 'reseau/Perso/Bureau/Wallpaper/scripts/patch_vscode_html.py');
                if (fs.existsSync(patchScript)) {
                    require('child_process').spawn('python3', [patchScript, filePath], { detached: true, stdio: 'ignore' }).unref();
                }

                // 4. Extraction dynamique des couleurs si activée
                if (wallpaper.colorEngine) {
                    try {
                        if (typeof wallpaper.colorEngine.extractCurrentColors === 'function') {
                            wallpaper.colorEngine.extractCurrentColors().catch(() => {});
                        } else if (typeof wallpaper.colorEngine.forceExtractNow === 'function') {
                            wallpaper.colorEngine.forceExtractNow().catch(() => {});
                        }
                    } catch (e) {}
                }

                vscode_1.default.window.showInformationMessage(`🖼️ Fond d\'écran appliqué et synchronisé avec le bureau : ${path.basename(filePath)}`);
            } catch (err) {
                vscode_1.default.window.showErrorMessage(`Erreur application fond d\'écran : ${err.message}`);
            }
        };

        if (choice.action === 'file') {
            const uris = await vscode_1.default.window.showOpenDialog({
                canSelectFiles: true,
                canSelectFolders: false,
                canSelectMany: false,
                title: 'Sélectionner un nouveau fond d\'écran',
                filters: {
                    'Vidéos et Images': ['mp4', 'webm', 'mkv', 'png', 'jpg', 'jpeg', 'webp', 'gif'],
                    'Vidéos': ['mp4', 'webm', 'mkv'],
                    'Images': ['png', 'jpg', 'jpeg', 'webp', 'gif'],
                    'Tous les fichiers': ['*']
                }
            });
            if (uris && uris.length > 0) {
                const selected = uris[0].fsPath;
                const isVideo = ['.mp4', '.webm', '.mkv'].some(ext => selected.toLowerCase().endsWith(ext));
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
                            const isVideo = ['.mp4', '.webm', '.mkv'].some(ext => destPath.toLowerCase().endsWith(ext));
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
                const isVideo = ['.mp4', '.webm', '.mkv'].some(ext => cur.toLowerCase().endsWith(ext));
                await updateStateAndApply(cur, isVideo ? 'video' : 'image');
            } else {
                vscode_1.default.window.showWarningMessage('Aucun fond d\'écran actif détecté sur le bureau.');
            }
        }
    }));

    // Surveillance continue pour synchroniser automatiquement VS Code si le Bureau change
    try {
        const homeDir = process.env.HOME || '/var/home/' + (process.env.USER || 'E256190S');
        const stateFilePath = path.join(homeDir, '.config/wallpapermaison/current_wallpaper.json');
        let lastSeenTimestamp = 0;
        const syncInterval = setInterval(() => {
            try {
                let currentDetected = null;
                if (fs.existsSync(stateFilePath)) {
                    const raw = fs.readFileSync(stateFilePath, 'utf8');
                    const data = JSON.parse(raw);
                    if (data && data.path) {
                        currentDetected = data.path;
                    }
                }
                if (!currentDetected) {
                    const { WallpaperBridge } = require('./colors/wallpaperBridge');
                    currentDetected = WallpaperBridge.detectCurrentWallpaper();
                }
                if (currentDetected && fs.existsSync(currentDetected)) {
                    const curCfg = wallpaper.getRawConfig();
                    if (curCfg.videoPath !== currentDetected) {
                        wallpaper.updateConfig({ videoPath: currentDetected, enabled: true }).catch(() => {});
                        const patchScript = path.join(homeDir, 'reseau/Perso/Bureau/Wallpaper/scripts/patch_vscode_html.py');
                        if (fs.existsSync(patchScript)) {
                            require('child_process').spawn('python3', [patchScript, currentDetected], { detached: true, stdio: 'ignore' }).unref();
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
                    }
                }
            } catch (err) {}
        }, 1000);
        context.subscriptions.push({ dispose: () => clearInterval(syncInterval) });
    } catch (e) {}

    // ── Sudo Root Terminal Integration ──
    function getRootShell() {
        const home = process.env.HOME || '/var/home/' + (process.env.USER || 'E256190S');
        const user = process.env.USER || 'E256190S';
        const candidates = [
            path.join(home, '.local/bin/root-shell'),
            path.join(home, 'reseau/Perso/.local/bin/root-shell'),
            `/var/home/${user}/.local/bin/root-shell`,
            '/var/home/E256190S/.local/bin/root-shell',
            'root-shell'
        ];
        for (const c of candidates) {
            if (c === 'root-shell' || fs.existsSync(c)) {
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
                    const home = process.env.HOME || '/var/home/' + (process.env.USER || 'E256190S');
                    const sf = path.join(home, '.config/wallpapermaison/current_wallpaper.json');
                    try {
                        if (fs.existsSync(sf)) {
                            const d = JSON.parse(fs.readFileSync(sf, 'utf8'));
                            return d.path || '';
                        }
                    } catch {}
                    return '';
                };

                const getHtml = (currentPath = '') => `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {
        padding: 16px 12px;
        font-family: var(--vscode-font-family, system-ui, sans-serif);
        font-size: var(--vscode-font-size, 13px);
        color: var(--vscode-foreground, #e5edf2);
        background: transparent;
        line-height: 1.4;
    }
    .card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 16px;
        text-align: center;
    }
    .badge {
        background: rgba(56, 189, 248, 0.18);
        border: 1px solid #38bdf8;
        color: #7dd3fc;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 8px;
    }
    .cur-title {
        font-weight: 600;
        font-size: 13px;
        margin-bottom: 6px;
    }
    .cur-path {
        font-size: 11px;
        color: #94a3b8;
        background: rgba(0, 0, 0, 0.25);
        padding: 6px 8px;
        border-radius: 4px;
        word-break: break-all;
    }
    button {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 11px 14px;
        margin-bottom: 10px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 600;
        transition: transform 0.1s ease, filter 0.15s ease;
    }
    .btn-main {
        background: linear-gradient(135deg, #0284c7, #2563eb);
        color: white;
        border: 1px solid #38bdf8;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
    }
    .btn-main:hover {
        filter: brightness(1.15);
        transform: translateY(-1px);
    }
    .btn-sub {
        background: rgba(255, 255, 255, 0.08);
        color: var(--vscode-foreground, #e5edf2);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .btn-sub:hover {
        background: rgba(255, 255, 255, 0.14);
    }
    .note {
        font-size: 11px;
        color: #94a3b8;
        text-align: center;
        margin-top: 14px;
    }
</style>
</head>
<body>
    <div class="card">
        <div class="badge">SYNC BUREAU &bull; LINUX</div>
        <div class="cur-title">Fond d\'Écran Actuel</div>
        <div class="cur-path" id="pathDisplay">${currentPath || 'Détection en cours...'}</div>
    </div>

    <button class="btn-main" id="btnFile">
        📁 Choisir un nouveau Wallpaper
    </button>

    <button class="btn-sub" id="btnUrl">
        🌐 Télécharger depuis un lien URL
    </button>

    <button class="btn-sub" id="btnSync">
        🔄 Synchroniser avec le bureau Linux
    </button>

    <div class="note">
        Toute modification s\'applique instantanément dans VS Code et sur votre bureau Linux.
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        document.getElementById('btnFile').onclick = () => vscode.postMessage({ command: 'chooseFile' });
        document.getElementById('btnUrl').onclick = () => vscode.postMessage({ command: 'chooseUrl' });
        document.getElementById('btnSync').onclick = () => vscode.postMessage({ command: 'syncDesktop' });

        window.addEventListener('message', e => {
            if (e.data && e.data.path) {
                document.getElementById('pathDisplay').textContent = e.data.path;
            }
        });
    </script>
</body>
</html>`;

                webviewView.webview.html = getHtml(getCurrentPath());

                webviewView.webview.onDidReceiveMessage(async (message) => {
                    if (message && message.command === 'chooseFile') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.chooseWallpaper');
                    } else if (message && message.command === 'chooseUrl') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.chooseWallpaper');
                    } else if (message && message.command === 'syncDesktop') {
                        vscode_1.default.commands.executeCommand('liveWallpaper.chooseWallpaper');
                    }
                });

                const interval = setInterval(() => {
                    const p = getCurrentPath();
                    webviewView.webview.postMessage({ path: p });
                }, 2000);
                webviewView.onDidDispose(() => clearInterval(interval));
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
//# sourceMappingURL=extension.js.map