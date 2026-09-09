"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
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
                await wallpaper.colorEngine.extractCurrentColors();
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
    // ── Sudo Root Terminal Integration ──
    const fs = require('fs');
    const path = require('path');
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