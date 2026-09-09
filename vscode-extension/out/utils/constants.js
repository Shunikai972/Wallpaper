"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TOUCH_FILE_PATH = exports.EXTENSION_ID = exports.CONFIG_SECTION = exports.EXTENSION_NAME = exports.PUBLISHER = exports.ENCODING = exports.LW_VER = exports.VERSION = void 0;
const node_path_1 = __importDefault(require("node:path"));
const package_json_1 = __importDefault(require("../../package.json"));
/** Version number */
exports.VERSION = package_json_1.default.version;
/** Patch marker identifier used to detect if workbench.html has been patched */
exports.LW_VER = 'live-wallpaper.ver';
/** File encoding */
exports.ENCODING = 'utf-8';
/** Publisher */
exports.PUBLISHER = package_json_1.default.publisher;
/** Extension name */
exports.EXTENSION_NAME = package_json_1.default.name;
/** Configuration section key */
exports.CONFIG_SECTION = 'liveWallpaper';
/** Extension ID (publisher.name) */
exports.EXTENSION_ID = `${exports.PUBLISHER}.${exports.EXTENSION_NAME}`;
/**
 * Touch file path — stores the path to workbench.html and marks first-install.
 * Stored next to compiled output so it persists across reloads.
 */
exports.TOUCH_FILE_PATH = node_path_1.default.join(__dirname, `../../lwb.${exports.VERSION}.touch`);
//# sourceMappingURL=constants.js.map