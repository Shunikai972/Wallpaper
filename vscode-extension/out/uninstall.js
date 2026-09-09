"use strict";
/**
 * Uninstall hook — runs when the extension is fully uninstalled.
 *
 * IMPORTANT:
 *  - The vscode API is NOT available here (runs outside extension host)
 *  - This file must NOT import from files that use the vscode module
 *  - All VSCode API uses must go through the `vsc` safe accessor
 *
 * This hook restores workbench.html to its original state so the video
 * wallpaper is removed even when the extension host cannot run cleanup.
 *
 * References:
 *  https://github.com/microsoft/vscode/issues/155561
 *  https://code.visualstudio.com/api/references/extension-manifest#extension-uninstall-hook
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const fs = __importStar(require("node:fs"));
// Import directly from source files — avoid re-exports that pull in vscode module
const PatchFile_html_1 = require("./liveWallpaper/PatchFile/PatchFile.html");
const constants_1 = require("./utils/constants");
async function uninstall() {
    try {
        // The touch file stores the workbench.html path recorded at install time
        const htmlPath = (await fs.promises.readFile(constants_1.TOUCH_FILE_PATH, constants_1.ENCODING)).trim();
        if (!htmlPath) {
            console.log('Live Wallpaper: No touch file content found — skipping cleanup.');
            return;
        }
        await new PatchFile_html_1.HtmlPatchFile(htmlPath).restore();
        console.log('Live Wallpaper: workbench.html restored successfully.');
    }
    catch (ex) {
        const msg = ex instanceof Error ? ex.message : String(ex);
        console.error('Live Wallpaper: Uninstall cleanup failed —', msg);
    }
}
uninstall();
//# sourceMappingURL=uninstall.js.map