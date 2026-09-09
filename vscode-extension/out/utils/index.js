"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports._ = void 0;
const sudo_prompt_1 = __importDefault(require("@vscode/sudo-prompt"));
const vsc_1 = require("./vsc");
var _;
(function (_) {
    /**
     * Detect if running in VSCode Desktop (as opposed to code-server / browser).
     * `desktop` → desktop app
     * `server-distro` → code-server
     */
    _.isDesktop = vsc_1.vsc?.env.appHost === 'desktop';
    /**
     * Execute a shell command with elevated privileges (sudo / UAC).
     *
     * @param cmd   Shell command to execute
     * @param options  Options passed to sudo-prompt (e.g. { name: 'My App' })
     */
    function sudoExec(cmd, options = {}) {
        return new Promise((resolve, reject) => {
            sudo_prompt_1.default.exec(cmd, options, (error) => {
                if (error) {
                    reject(error);
                }
                else {
                    resolve();
                }
            });
        });
    }
    _.sudoExec = sudoExec;
    /**
     * Wrap a JS string in an Immediately Invoked Function Expression (IIFE).
     *
     * @param source  JavaScript source code
     */
    function withIIFE(source) {
        return `;(function() { ${source} })();`;
    }
    _.withIIFE = withIIFE;
})(_ || (exports._ = _ = {}));
//# sourceMappingURL=index.js.map