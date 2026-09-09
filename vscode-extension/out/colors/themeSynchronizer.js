"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ThemeSynchronizer = void 0;

const vscode_1 = __importDefault(require("vscode"));

class ThemeSynchronizer {
    constructor() {
        this.appliedKeys = new Set();
        this.appliedTokens = false;
    }

    buildWorkbenchColors(palette, mode = "full") {
        if (mode === "accent-only") {
            return {
                "activityBar.activeBorder": palette.accent,
                "activityBarBadge.background": palette.accent,
                "activityBarBadge.foreground": "#ffffff",
                "editorCursor.foreground": palette.cursor,
                "editor.selectionBackground": palette.selection,
                "tab.activeBorder": palette.accent,
                "tab.activeBorderTop": palette.accent,
                "statusBar.background": palette.statusBarBackground,
                "statusBar.foreground": palette.statusBarForeground,
                "focusBorder": palette.accent,
                "button.background": palette.accent,
                "button.foreground": "#ffffff",
                "badge.background": palette.accent,
                "badge.foreground": "#ffffff"
            };
        }

        // Mode "full"
        return {
            "editor.background": palette.editorBackground,
            "editor.foreground": palette.editorForeground,
            "editorCursor.foreground": palette.cursor,
            "editor.selectionBackground": palette.selection,
            "editor.lineHighlightBackground": palette.activeTabBackground + "33",
            "editorLineNumber.foreground": palette.mutedForeground + "77",
            "editorLineNumber.activeForeground": palette.editorForeground,

            "activityBar.background": palette.sidebarBackground,
            "activityBar.foreground": palette.editorForeground,
            "activityBar.activeBorder": palette.accent,
            "activityBarBadge.background": palette.accent,
            "activityBarBadge.foreground": "#ffffff",

            "sideBar.background": palette.sidebarBackground,
            "sideBar.foreground": palette.editorForeground,
            "sideBarTitle.foreground": palette.editorForeground,
            "sideBarSectionHeader.background": palette.editorBackground,
            "sideBarSectionHeader.foreground": palette.editorForeground,

            "statusBar.background": palette.statusBarBackground,
            "statusBar.foreground": palette.statusBarForeground,
            "statusBarItem.hoverBackground": palette.accent + "33",

            "tab.activeBackground": palette.activeTabBackground,
            "tab.activeForeground": palette.editorForeground,
            "tab.inactiveBackground": palette.sidebarBackground,
            "tab.inactiveForeground": palette.mutedForeground,
            "tab.activeBorder": palette.accent,
            "tab.activeBorderTop": palette.accent,

            "titleBar.activeBackground": palette.editorBackground,
            "titleBar.activeForeground": palette.editorForeground,
            "titleBar.inactiveBackground": palette.sidebarBackground,
            "titleBar.inactiveForeground": palette.mutedForeground,

            "terminal.background": palette.editorBackground,
            "terminal.foreground": palette.editorForeground,

            "focusBorder": palette.accent,
            "badge.background": palette.accent,
            "badge.foreground": "#ffffff",
            "button.background": palette.accent,
            "button.foreground": "#ffffff"
        };
    }

    buildTokenColors(palette, mode = "full") {
        if (mode === "accent-only") return null;

        return {
            "textMateRules": [
                {
                    "scope": ["comment", "punctuation.definition.comment"],
                    "settings": { "foreground": palette.mutedForeground }
                },
                {
                    "scope": ["keyword", "storage.type", "storage.modifier"],
                    "settings": { "foreground": palette.accent, "fontStyle": "bold" }
                },
                {
                    "scope": ["string", "string.quoted"],
                    "settings": { "foreground": palette.secondary }
                },
                {
                    "scope": ["entity.name.function", "support.function"],
                    "settings": { "foreground": palette.cursor }
                },
                {
                    "scope": ["constant.numeric", "constant.language"],
                    "settings": { "foreground": palette.secondary }
                },
                {
                    "scope": ["entity.name.type", "support.type"],
                    "settings": { "foreground": palette.accent }
                }
            ]
        };
    }

    async apply(palette, mode = "full") {
        const colors = this.buildWorkbenchColors(palette, mode);
        const tokens = this.buildTokenColors(palette, mode);

        const config = vscode_1.default.workspace.getConfiguration();
        const existingColors = config.get("workbench.colorCustomizations") || {};
        const mergedColors = { ...existingColors, ...colors };

        // Enregistrer les clés modifiées pour pouvoir les nettoyer
        Object.keys(colors).forEach((k) => this.appliedKeys.add(k));

        await config.update("workbench.colorCustomizations", mergedColors, vscode_1.default.ConfigurationTarget.Global);

        if (tokens) {
            this.appliedTokens = true;
            await config.update("editor.tokenColorCustomizations", tokens, vscode_1.default.ConfigurationTarget.Global);
        }
    }

    async clear() {
        if (this.appliedKeys.size === 0 && !this.appliedTokens) return;

        const config = vscode_1.default.workspace.getConfiguration();
        const existingColors = config.get("workbench.colorCustomizations") || {};
        const cleanedColors = { ...existingColors };

        for (const k of this.appliedKeys) {
            delete cleanedColors[k];
        }
        this.appliedKeys.clear();

        const hasKeys = Object.keys(cleanedColors).length > 0;
        await config.update("workbench.colorCustomizations", hasKeys ? cleanedColors : undefined, vscode_1.default.ConfigurationTarget.Global);

        if (this.appliedTokens) {
            this.appliedTokens = false;
            await config.update("editor.tokenColorCustomizations", undefined, vscode_1.default.ConfigurationTarget.Global);
        }
    }
}

exports.ThemeSynchronizer = ThemeSynchronizer;
