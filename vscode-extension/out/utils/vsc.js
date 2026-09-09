"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.vsc = void 0;
/**
 * Safe accessor for the vscode API.
 *
 * When the uninstall hook runs (`vscode:uninstall`), the vscode module is
 * unavailable because it runs outside the extension host. All other code
 * paths have access to vscode.
 */
let vsc;
try {
    exports.vsc = vsc = require('vscode');
}
catch {
    exports.vsc = vsc = undefined;
}
//# sourceMappingURL=vsc.js.map