"use strict";
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AbsPatchFile = exports.EFilePatchType = void 0;
const node_crypto_1 = require("node:crypto");
const node_fs_1 = __importStar(require("node:fs"));
const node_os_1 = require("node:os");
const node_path_1 = __importDefault(require("node:path"));
const utils_1 = require("../../utils");
const constants_1 = require("../../utils/constants");
const vsc_1 = require("../../utils/vsc");
/** Describes the current patch state of a file */
var EFilePatchType;
(function (EFilePatchType) {
    /** File has not been patched */
    EFilePatchType[EFilePatchType["None"] = 0] = "None";
    /** File was patched by an older version */
    EFilePatchType[EFilePatchType["Legacy"] = 1] = "Legacy";
    /** File is patched by the current version */
    EFilePatchType[EFilePatchType["Latest"] = 2] = "Latest";
})(EFilePatchType || (exports.EFilePatchType = EFilePatchType = {}));
/**
 * Abstract base class for patching VSCode workbench files.
 * Handles reading, writing (with sudo fallback), and version detection.
 */
class AbsPatchFile {
    filePath;
    constructor(filePath) {
        this.filePath = filePath;
    }
    /**
     * Returns true if the file has been patched (any version).
     */
    async hasPatched() {
        const patchType = await this.getPatchType();
        return patchType !== EFilePatchType.None;
    }
    /**
     * Determine the current patch state of the file.
     * Returns EFilePatchType.None gracefully if the file cannot be read.
     */
    async getPatchType() {
        let content;
        try {
            content = await this.getContent();
        }
        catch {
            // File doesn't exist or can't be read — treat as unpatched
            return EFilePatchType.None;
        }
        // Patched by current version
        if (content.includes(`${constants_1.LW_VER}.${constants_1.VERSION}`)) {
            return EFilePatchType.Latest;
        }
        // Patched by an older version
        if (content.includes(constants_1.LW_VER)) {
            return EFilePatchType.Legacy;
        }
        return EFilePatchType.None;
    }
    /** Read the file as UTF-8 text */
    getContent() {
        return node_fs_1.default.promises.readFile(this.filePath, constants_1.ENCODING);
    }
    /**
     * Write content to a file path.
     * On permission errors, prompts the user to retry with admin/sudo.
     */
    async saveContentTo(filePath, content) {
        try {
            if (node_fs_1.default.existsSync(filePath)) {
                await node_fs_1.default.promises.access(filePath, node_fs_1.constants.W_OK);
            }
            await node_fs_1.default.promises.writeFile(filePath, content, constants_1.ENCODING);
            return true;
        }
        catch (e) {
            if (!vsc_1.vsc) {
                return false;
            }
            const msg = e instanceof Error ? e.message : String(e);
            // Si le système de fichiers est monté en lecture seule (EROFS) ou /usr sysext
            if (e.code === 'EROFS' || msg.includes('read-only') || filePath.startsWith('/usr/')) {
                vsc_1.vsc.window.showInformationMessage(
                    `Live Wallpaper : L'installation de VS Code est en lecture seule (${e.code || 'EROFS'}). Le mode officiel sans modification de fichiers système est actif (couleurs dynamiques et lecteur Webview opérationnels).`
                );
                return false;
            }
            const retry = 'Retry with Admin / Sudo';
            const result = await vsc_1.vsc.window.showErrorMessage(`Live Wallpaper: Cannot write to file — ${msg}`, retry);
            if (result !== retry) {
                return false;
            }
            // Write content to a temp file then move it with sudo
            const tempFilePath = node_path_1.default.join((0, node_os_1.tmpdir)(), `live-wallpaper-${(0, node_crypto_1.randomUUID)()}.temp`);
            await node_fs_1.default.promises.writeFile(tempFilePath, content, constants_1.ENCODING);
            try {
                const mvCmd = process.platform === 'win32' ? 'move /Y' : 'mv -f';
                await utils_1._.sudoExec(`${mvCmd} "${tempFilePath}" "${filePath}"`, {
                    name: 'Live Wallpaper Extension',
                });
                return true;
            }
            catch (sudoErr) {
                const sudoMsg = sudoErr instanceof Error
                    ? sudoErr.message
                    : String(sudoErr);
                vsc_1.vsc.window.showErrorMessage(`Live Wallpaper: Sudo failed — ${sudoMsg}`);
                return false;
            }
            finally {
                await node_fs_1.default.promises.rm(tempFilePath, { force: true });
            }
        }
    }
    /** Write content to the target file */
    async write(content) {
        if (!content.trim().length) {
            return false;
        }
        return this.saveContentTo(this.filePath, content);
    }
    /**
     * Restore the file to its original (unpatched) state.
     */
    async restore() {
        try {
            const curContent = await this.getContent();
            const cleaned = this.cleanPatches(curContent);
            // Nothing changed — already clean
            if (curContent === cleaned) {
                return true;
            }
            return await this.write(cleaned);
        }
        catch {
            return false;
        }
    }
}
exports.AbsPatchFile = AbsPatchFile;
//# sourceMappingURL=PatchFile.base.js.map