"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.vscodePath = void 0;
const node_fs_1 = __importDefault(require("node:fs"));
const node_path_1 = __importDefault(require("node:path"));
const index_1 = require("./index");
const vsc_1 = require("./vsc");
/**
 * Resolve the base "out" directory of the running VSCode instance.
 *
 * Strategy (in order of preference):
 *  1. `require.main?.filename` — available in some VSCode setups
 *  2. `vscode.env.appRoot` — always available in the extension host; points to
 *     the app root (one level above "out")
 *
 * On desktop: …/resources/app/out
 * On code-server: …/vscode/out
 */
const base = (() => {
    const mainFilename = require.main?.filename;
    if (mainFilename?.length) {
        return node_path_1.default.dirname(mainFilename);
    }
    // appRoot = …/resources/app  →  base = …/resources/app/out
    const appRoot = vsc_1.vsc?.env.appRoot;
    if (appRoot) {
        return node_path_1.default.join(appRoot, 'out');
    }
    return '';
})();
/**
 * Candidates for workbench.html path on desktop VSCode.
 *
 * VSCode has used different sub-paths across versions:
 *  - electron-browser  (older / current stable)
 *  - electron-sandbox  (newer builds)
 *
 * We probe both and return the first one that exists.
 */
function resolveDesktopHtmlPath(outDir) {
    const candidates = [
        node_path_1.default.join(outDir, 'vs/code/electron-browser/workbench/workbench.html'),
        node_path_1.default.join(outDir, 'vs/code/electron-sandbox/workbench/workbench.html'),
    ];
    for (const candidate of candidates) {
        if (node_fs_1.default.existsSync(candidate)) {
            return candidate;
        }
    }
    // Return the first candidate as fallback (error will surface later with a clear message)
    return candidates[0];
}
const workbenchHtmlPath = (() => {
    if (index_1._.isDesktop) {
        return resolveDesktopHtmlPath(base);
    }
    // code-server / browser
    return node_path_1.default.join(base, 'vs/code/browser/workbench/workbench.html');
})();
exports.vscodePath = {
    /** Base "out" directory of the VSCode installation */
    base,
    /** Root directory of this extension */
    extRoot: node_path_1.default.join(__dirname, '../../'),
    /** Path to workbench.html */
    workbenchHtmlPath,
};
//# sourceMappingURL=vscodePath.js.map