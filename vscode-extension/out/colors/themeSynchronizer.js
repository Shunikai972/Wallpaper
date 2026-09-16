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
            "editor.background": "#00000000",
            "editorGroup.emptyBackground": "#00000000",
            "editor.foreground": palette.editorForeground,
            "editorCursor.foreground": palette.cursor,
            "editor.selectionBackground": palette.selection,
            "editor.lineHighlightBackground": "#ffffff0d",
            "editorLineNumber.foreground": palette.mutedForeground,
            "editorLineNumber.activeForeground": palette.editorForeground,
            "editorIndentGuide.background": "#ffffff1a",
            "editorIndentGuide.activeBackground": palette.accent + "88",
            "editorBracketMatch.background": palette.accent + "33",
            "editorBracketMatch.border": palette.accent,

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

        const tokens = palette.tokens || {
            keyword: palette.accent,
            function: palette.cursor,
            string: palette.secondary,
            number: palette.secondary,
            type: palette.accent,
            variable: palette.editorForeground,
            property: palette.secondary,
            comment: palette.mutedForeground,
            operator: palette.editorForeground,
            constant: palette.secondary,
            tag: palette.accent
        };

        return {
            "textMateRules": [
                {
                    "name": "Comments",
                    "scope": [
                        "comment",
                        "comment.line",
                        "comment.block",
                        "punctuation.definition.comment",
                        "comment.block.documentation"
                    ],
                    "settings": { "foreground": tokens.comment, "fontStyle": "italic" }
                },
                {
                    "name": "Keywords and Storage",
                    "scope": [
                        "keyword",
                        "keyword.control",
                        "keyword.control.conditional",
                        "keyword.control.loop",
                        "keyword.control.flow",
                        "storage",
                        "storage.type",
                        "storage.modifier",
                        "keyword.operator.new",
                        "keyword.operator.expression"
                    ],
                    "settings": { "foreground": tokens.keyword, "fontStyle": "bold" }
                },
                {
                    "name": "Functions and Methods",
                    "scope": [
                        "entity.name.function",
                        "support.function",
                        "entity.name.method",
                        "meta.function-call",
                        "variable.function"
                    ],
                    "settings": { "foreground": tokens.function, "fontStyle": "bold" }
                },
                {
                    "name": "Strings and Templates",
                    "scope": [
                        "string",
                        "string.quoted",
                        "string.quoted.single",
                        "string.quoted.double",
                        "string.template",
                        "string.interpolated",
                        "punctuation.definition.string"
                    ],
                    "settings": { "foreground": tokens.string }
                },
                {
                    "name": "Numbers and Numeric Constants",
                    "scope": [
                        "constant.numeric",
                        "constant.numeric.integer",
                        "constant.numeric.float",
                        "constant.numeric.hex"
                    ],
                    "settings": { "foreground": tokens.number, "fontStyle": "bold" }
                },
                {
                    "name": "Constants and Language Builtins",
                    "scope": [
                        "constant.language",
                        "constant.other",
                        "support.constant",
                        "constant.language.boolean"
                    ],
                    "settings": { "foreground": tokens.constant, "fontStyle": "bold" }
                },
                {
                    "name": "Types, Classes and Interfaces",
                    "scope": [
                        "entity.name.type",
                        "entity.name.class",
                        "entity.name.struct",
                        "entity.name.interface",
                        "support.type",
                        "support.class",
                        "entity.other.inherited-class"
                    ],
                    "settings": { "foreground": tokens.type, "fontStyle": "bold" }
                },
                {
                    "name": "Variables and Parameters",
                    "scope": [
                        "variable",
                        "variable.other",
                        "variable.parameter",
                        "variable.language.this",
                        "variable.language.special"
                    ],
                    "settings": { "foreground": tokens.variable }
                },
                {
                    "name": "Properties and Object Keys",
                    "scope": [
                        "variable.other.property",
                        "variable.other.object.property",
                        "support.type.property-name",
                        "meta.object-literal.key"
                    ],
                    "settings": { "foreground": tokens.property }
                },
                {
                    "name": "HTML/XML Tags and Attributes",
                    "scope": [
                        "entity.name.tag",
                        "entity.other.attribute-name"
                    ],
                    "settings": { "foreground": tokens.tag }
                },
                {
                    "name": "Operators and Punctuation",
                    "scope": [
                        "keyword.operator",
                        "keyword.operator.assignment",
                        "keyword.operator.comparison",
                        "punctuation.separator",
                        "punctuation.terminator"
                    ],
                    "settings": { "foreground": tokens.operator }
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

    async clearColorCustomizations() {
        return this.clear();
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
