"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WebviewPlayer = void 0;

const vscode_1 = __importDefault(require("vscode"));
const node_fs_1 = __importDefault(require("node:fs"));
const wallpaperBridge_1 = require("../colors/wallpaperBridge");

class WebviewPlayer {
    static currentPanel = undefined;

    static createOrShow(extensionUri, mediaPath = null) {
        const column = vscode_1.default.window.activeTextEditor
            ? vscode_1.default.window.activeTextEditor.viewColumn
            : undefined;

        if (WebviewPlayer.currentPanel) {
            WebviewPlayer.currentPanel.panel.reveal(column);
            if (mediaPath) WebviewPlayer.currentPanel.setMedia(mediaPath);
            return;
        }

        const panel = vscode_1.default.window.createWebviewPanel(
            'liveWallpaperPlayer',
            'Live Wallpaper Player',
            column || vscode_1.default.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [vscode_1.default.Uri.file('/')]
            }
        );

        WebviewPlayer.currentPanel = new WebviewPlayer(panel, extensionUri, mediaPath);
    }

    constructor(panel, extensionUri, mediaPath) {
        this.panel = panel;
        this.extensionUri = extensionUri;
        this.mediaPath = mediaPath || wallpaperBridge_1.WallpaperBridge.detectCurrentWallpaper() || '';

        this.updateContent();

        this.panel.onDidDispose(() => {
            WebviewPlayer.currentPanel = undefined;
        });

        this.panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'selectFile') {
                const uris = await vscode_1.default.window.showOpenDialog({
                    canSelectFiles: true,
                    canSelectFolders: false,
                    canSelectMany: false,
                    filters: {
                        'Vidéos & Images': ['mp4', 'webm', 'mkv', 'png', 'jpg', 'jpeg', 'webp', 'gif']
                    }
                });
                if (uris && uris.length > 0) {
                    this.setMedia(uris[0].fsPath);
                }
            } else if (msg.command === 'applyColors') {
                await vscode_1.default.commands.executeCommand('liveWallpaper.extractNow');
                vscode_1.default.window.showInformationMessage('Live Wallpaper : Couleurs appliquées avec succès au thème !');
            }
        });
    }

    setMedia(filePath) {
        this.mediaPath = filePath;
        this.updateContent();
    }

    updateContent() {
        const isVideo = !['.png', '.jpg', '.jpeg', '.webp', '.bmp'].some(ext => this.mediaPath.toLowerCase().endsWith(ext));
        const fileExists = this.mediaPath && node_fs_1.default.existsSync(this.mediaPath);
        const webviewUri = fileExists ? this.panel.webview.asWebviewUri(vscode_1.default.Uri.file(this.mediaPath)) : '';

        this.panel.webview.html = `
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        margin: 0;
                        padding: 20px;
                        background: #0d1117;
                        color: #e6edf3;
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        min-height: 100vh;
                        box-sizing: border-box;
                    }
                    .container {
                        max-width: 900px;
                        width: 100%;
                        background: #161b22;
                        border: 1px solid #30363d;
                        border-radius: 12px;
                        padding: 24px;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                    }
                    h2 { margin-top: 0; color: #58a6ff; display: flex; align-items: center; gap: 8px; }
                    .viewport {
                        width: 100%;
                        height: 460px;
                        background: #000;
                        border-radius: 8px;
                        overflow: hidden;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        position: relative;
                        border: 1px solid #30363d;
                        margin: 16px 0;
                    }
                    video, img {
                        width: 100%;
                        height: 100%;
                        object-fit: cover;
                    }
                    .controls {
                        display: flex;
                        gap: 12px;
                        margin-top: 16px;
                        flex-wrap: wrap;
                    }
                    button {
                        background: #238636;
                        color: white;
                        border: none;
                        padding: 10px 18px;
                        border-radius: 6px;
                        font-weight: 600;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    button.secondary { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; }
                    button:hover { opacity: 0.9; }
                    .info { font-size: 13px; color: #8b949e; word-break: break-all; margin-top: 8px; }
                    .badge {
                        display: inline-block;
                        padding: 2px 8px;
                        background: #1f6feb22;
                        border: 1px solid #388bfd44;
                        color: #58a6ff;
                        border-radius: 20px;
                        font-size: 12px;
                        margin-bottom: 8px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <span class="badge">✨ Mode Haute Fidélité Adaptatif</span>
                    <h2>🌌 Live Wallpaper Player</h2>
                    <div class="info">Média actif : <strong>${this.mediaPath || 'Aucun fichier sélectionné'}</strong></div>

                    <div class="viewport">
                        ${!fileExists ? '<div style="color:#8b949e;">Aucun wallpaper chargé. Choisissez un fichier ci-dessous.</div>' :
                          (isVideo ?
                            `<video src="${webviewUri}" autoplay loop muted playsinline></video>` :
                            `<img src="${webviewUri}" alt="Wallpaper" />`
                          )}
                    </div>

                    <div class="controls">
                        <button onclick="selectFile()">📁 Changer de Wallpaper</button>
                        <button class="secondary" onclick="applyColors()">🎨 Synchroniser les couleurs maintenant</button>
                    </div>
                </div>

                <script>
                    const vscode = acquireVsCodeApi();
                    function selectFile() { vscode.postMessage({ command: 'selectFile' }); }
                    function applyColors() { vscode.postMessage({ command: 'applyColors' }); }
                </script>
            </body>
            </html>
        `;
    }
}

exports.WebviewPlayer = WebviewPlayer;
