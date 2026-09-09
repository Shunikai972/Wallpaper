"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TemporalSmoother = void 0;

const colorimetry_1 = require("./colorimetry");

class TemporalSmoother {
    constructor(smoothing = 0.35, changeThreshold = 7.0) {
        this.smoothing = smoothing;
        this.changeThreshold = changeThreshold;
        this.currentPalette = null;
    }

    setSmoothing(s) {
        this.smoothing = Math.max(0.05, Math.min(1.0, s));
    }

    setChangeThreshold(t) {
        this.changeThreshold = Math.max(1.0, t);
    }

    /**
     * Calcule la différence perceptive moyenne entre l'ancienne et la nouvelle palette.
     */
    computePaletteDistance(p1, p2) {
        if (!p1 || !p2 || !p1.raw || !p2.raw) return 100.0;
        const lab1Dom = colorimetry_1.Colorimetry.rgbToLab(...p1.raw.dominant);
        const lab2Dom = colorimetry_1.Colorimetry.rgbToLab(...p2.raw.dominant);
        const dDom = colorimetry_1.Colorimetry.deltaE(lab1Dom, lab2Dom);

        const lab1Acc = colorimetry_1.Colorimetry.rgbToLab(...p1.raw.accent);
        const lab2Acc = colorimetry_1.Colorimetry.rgbToLab(...p2.raw.accent);
        const dAcc = colorimetry_1.Colorimetry.deltaE(lab1Acc, lab2Acc);

        return (dDom * 0.6) + (dAcc * 0.4);
    }

    /**
     * Applique le filtre d'hystérésis et le lissage temporel.
     * @param targetPalette Nouvelle palette calculée
     * @param force Si true, ignore le seuil et applique immédiatement (ex: changement de wallpaper)
     * @returns Palette lissée, ou null si la variation est sous le seuil d'hystérésis.
     */
    smooth(targetPalette, force = false) {
        if (!this.currentPalette || force) {
            this.currentPalette = targetPalette;
            return targetPalette;
        }

        const dist = this.computePaletteDistance(this.currentPalette, targetPalette);
        if (dist < this.changeThreshold) {
            // Variation imperceptible -> aucun changement (anti-scintillement)
            return null;
        }

        // LERP sur chaque composante colorimétrique
        const t = this.smoothing;
        const cur = this.currentPalette.raw;
        const tgt = targetPalette.raw;

        const newDom = colorimetry_1.Colorimetry.lerpColor(cur.dominant, tgt.dominant, t);
        const newSec = colorimetry_1.Colorimetry.lerpColor(cur.secondary, tgt.secondary, t);
        const newAcc = colorimetry_1.Colorimetry.lerpColor(cur.accent, tgt.accent, t);
        const newDarkBg = colorimetry_1.Colorimetry.lerpColor(cur.darkBg, tgt.darkBg, t);
        const newSidebarBg = colorimetry_1.Colorimetry.lerpColor(cur.sidebarBg, tgt.sidebarBg, t);
        const newActiveBg = colorimetry_1.Colorimetry.lerpColor(cur.activeBg, tgt.activeBg, t);

        // Garantie de contraste maintenue sur les couleurs interpolées
        const newFg = colorimetry_1.Colorimetry.ensureContrast(
            colorimetry_1.Colorimetry.lerpColor(cur.fg, tgt.fg, t),
            newDarkBg,
            7.0
        );
        const newMuted = colorimetry_1.Colorimetry.ensureContrast(
            colorimetry_1.Colorimetry.lerpColor(cur.muted, tgt.muted, t),
            newDarkBg,
            4.5
        );
        const newCursor = colorimetry_1.Colorimetry.ensureContrast(newAcc, newDarkBg, 5.0);

        const smoothedPalette = {
            dominant: colorimetry_1.Colorimetry.rgbToHex(...newDom),
            secondary: colorimetry_1.Colorimetry.rgbToHex(...newSec),
            accent: colorimetry_1.Colorimetry.rgbToHex(...newAcc),
            editorBackground: colorimetry_1.Colorimetry.rgbToHex(...newDarkBg),
            sidebarBackground: colorimetry_1.Colorimetry.rgbToHex(...newSidebarBg),
            activeTabBackground: colorimetry_1.Colorimetry.rgbToHex(...newActiveBg),
            editorForeground: colorimetry_1.Colorimetry.rgbToHex(...newFg),
            mutedForeground: colorimetry_1.Colorimetry.rgbToHex(...newMuted),
            cursor: colorimetry_1.Colorimetry.rgbToHex(...newCursor),
            selection: colorimetry_1.Colorimetry.rgbToHex(newAcc[0], newAcc[1], newAcc[2], 60),
            statusBarBackground: colorimetry_1.Colorimetry.rgbToHex(...newDom),
            statusBarForeground: colorimetry_1.Colorimetry.rgbToHex(...colorimetry_1.Colorimetry.ensureContrast([255, 255, 255], newDom, 4.5)),
            contrastRatio: colorimetry_1.Colorimetry.contrastRatio(newFg, newDarkBg),
            raw: {
                dominant: newDom,
                secondary: newSec,
                accent: newAcc,
                darkBg: newDarkBg,
                sidebarBg: newSidebarBg,
                activeBg: newActiveBg,
                fg: newFg,
                muted: newMuted
            }
        };

        this.currentPalette = smoothedPalette;
        return smoothedPalette;
    }

    reset() {
        this.currentPalette = null;
    }
}

exports.TemporalSmoother = TemporalSmoother;
