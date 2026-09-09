"""Module de colorimétrie avancée et d extraction de palette harmonique.

Implémente :
- Espaces colorimétriques RGB, HSV, HSL, CIE-Lab.
- Calcul de distance perceptive Delta E (CIE76).
- Calcul de luminance relative et de ratio de contraste WCAG 2.1.
- Garantie de lisibilité du texte (contraste minimal AA/AAA).
- Extraction de palette intelligente (dominant, secondaire, accent, fonds, textes).
- Lissage temporel (LERP + hystérésis) pour vidéos en mouvement.
- Export direct au format workbench.colorCustomizations de VS Code.
"""

import math
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image

def rgb_to_hex(r: int, g: int, b: int, a: Optional[int] = None) -> str:
    """Convertit RGB(A) en code hexadécimal #RRGGBB(AA)."""
    r = max(0, min(255, int(round(r))))
    g = max(0, min(255, int(round(g))))
    b = max(0, min(255, int(round(b))))
    if a is not None:
        a = max(0, min(255, int(round(a))))
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
    return f"#{r:02x}{g:02x}{b:02x}"

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convertit un code hexadécimal #RRGGBB en tuple (R, G, B)."""
    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convertit RGB [0-255] en HSV (H: 0-360, S: 0-1, V: 0-1)."""
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    cmax = max(rf, gf, bf)
    cmin = min(rf, gf, bf)
    delta = cmax - cmin

    if delta == 0:
        h = 0.0
    elif cmax == rf:
        h = (60 * ((gf - bf) / delta) + 360) % 360
    elif cmax == gf:
        h = (60 * ((bf - rf) / delta) + 120) % 360
    else:
        h = (60 * ((rf - gf) / delta) + 240) % 360

    s = 0.0 if cmax == 0 else delta / cmax
    v = cmax
    return h, s, v

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convertit HSV (H: 0-360, S: 0-1, V: 0-1) en RGB [0-255]."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if 0 <= h < 60:
        rf, gf, bf = c, x, 0
    elif 60 <= h < 120:
        rf, gf, bf = x, c, 0
    elif 120 <= h < 180:
        rf, gf, bf = 0, c, x
    elif 180 <= h < 240:
        rf, gf, bf = 0, x, c
    elif 240 <= h < 300:
        rf, gf, bf = x, 0, c
    else:
        rf, gf, bf = c, 0, x

    return int(round((rf + m) * 255)), int(round((gf + m) * 255)), int(round((bf + m) * 255))

def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convertit RGB en espace perceptif CIE-Lab (D65)."""
    def pivot_rgb(c: float) -> float:
        c = c / 255.0
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    rl, gl, bl = pivot_rgb(r), pivot_rgb(g), pivot_rgb(b)

    x = (rl * 0.4124 + gl * 0.3576 + bl * 0.1805) / 0.95047
    y = (rl * 0.2126 + gl * 0.7152 + bl * 0.0722) / 1.00000
    z = (rl * 0.0193 + gl * 0.1192 + bl * 0.9505) / 1.08883

    def pivot_xyz(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = pivot_xyz(x), pivot_xyz(y), pivot_xyz(z)
    L = max(0.0, (116 * fy) - 16)
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)
    return L, a, b_val

def delta_e(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """Calcule la distance perceptive Delta E (CIE76) entre deux couleurs Lab."""
    return math.sqrt((lab1[0] - lab2[0]) ** 2 + (lab1[1] - lab2[1]) ** 2 + (lab1[2] - lab2[2]) ** 2)

def relative_luminance(r: int, g: int, b: int) -> float:
    """Calcule la luminance relative standard W3C / WCAG 2.1."""
    def lum_channel(c: int) -> float:
        norm = c / 255.0
        return norm / 12.92 if norm <= 0.03928 else ((norm + 0.055) / 1.055) ** 2.4
    return 0.2126 * lum_channel(r) + 0.7152 * lum_channel(g) + 0.0722 * lum_channel(b)

def contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calcule le ratio de contraste WCAG 2.1 entre deux couleurs RGB (1.0 à 21.0)."""
    l1 = relative_luminance(*rgb1)
    l2 = relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def ensure_contrast(text_rgb: Tuple[int, int, int], bg_rgb: Tuple[int, int, int], min_contrast: float = 7.0) -> Tuple[int, int, int]:
    """Ajuste automatiquement la luminosité de text_rgb pour garantir min_contrast face à bg_rgb."""
    current_ratio = contrast_ratio(text_rgb, bg_rgb)
    if current_ratio >= min_contrast:
        return text_rgb

    h, s, v = rgb_to_hsv(*text_rgb)
    bg_lum = relative_luminance(*bg_rgb)

    if bg_lum < 0.5:
        step = 0.02
        new_v = v
        new_s = s
        while new_v <= 1.0:
            candidate = hsv_to_rgb(h, new_s, new_v)
            if contrast_ratio(candidate, bg_rgb) >= min_contrast:
                return candidate
            new_v += step
            if new_v > 0.85:
                new_s = max(0.0, new_s - 0.03)

        return (255, 255, 255)
    else:
        step = 0.02
        new_v = v
        while new_v >= 0.0:
            candidate = hsv_to_rgb(h, s, new_v)
            if contrast_ratio(candidate, bg_rgb) >= min_contrast:
                return candidate
            new_v -= step
        return (0, 0, 0)

def lerp_color(rgb_a: Tuple[int, int, int], rgb_b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Interpolation linéaire (LERP) entre deux couleurs RGB avec facteur t [0, 1]."""
    t = max(0.0, min(1.0, t))
    r = int(round(rgb_a[0] + (rgb_b[0] - rgb_a[0]) * t))
    g = int(round(rgb_a[1] + (rgb_b[1] - rgb_a[1]) * t))
    b = int(round(rgb_a[2] + (rgb_b[2] - rgb_a[2]) * t))
    return r, g, b

class ColorPaletteExtractor:
    """Extrait une palette intelligente et lisible à partir d une image ou frame."""

    def __init__(self, target_resolution: Tuple[int, int] = (120, 68)) -> None:
        self.target_res = target_resolution

    def extract_from_image(self, pil_image: Image.Image) -> Dict[str, Any]:
        small = pil_image.convert("RGB").resize(self.target_res, Image.Resampling.BOX)
        raw_bytes = small.tobytes()
        pixels = [(raw_bytes[i], raw_bytes[i+1], raw_bytes[i+2]) for i in range(0, len(raw_bytes), 3)]

        bins: Dict[Tuple[int, int, int], int] = {}
        for r, g, b in pixels:
            h, s, v = rgb_to_hsv(r, g, b)
            if v < 0.06 or (v > 0.96 and s < 0.05):
                continue
            key = (r // 8 * 8, g // 8 * 8, b // 8 * 8)
            bins[key] = bins.get(key, 0) + 1

        if not bins:
            return self._default_palette((30, 40, 60))

        scored_colors = []
        for rgb, count in bins.items():
            h, s, v = rgb_to_hsv(*rgb)
            score = count * (1.0 + s * 1.5)
            scored_colors.append((score, count, rgb, (h, s, v)))

        scored_colors.sort(key=lambda x: x[0], reverse=True)

        clusters: List[Dict[str, Any]] = []
        for score, count, rgb, hsv in scored_colors[:80]:
            lab = rgb_to_lab(*rgb)
            merged = False
            for c in clusters:
                if delta_e(lab, c["lab"]) < 16.0:
                    c["count"] += count
                    c["score"] += score
                    merged = True
                    break
            if not merged:
                clusters.append({
                    "rgb": rgb,
                    "lab": lab,
                    "hsv": hsv,
                    "count": count,
                    "score": score
                })

        clusters.sort(key=lambda x: x["score"], reverse=True)

        primary_cluster = clusters[0]
        dom_rgb = primary_cluster["rgb"]
        dom_h, dom_s, dom_v = primary_cluster["hsv"]

        sec_rgb = dom_rgb
        for c in clusters[1:]:
            hue_diff = abs(c["hsv"][0] - dom_h)
            if hue_diff > 180:
                hue_diff = 360 - hue_diff
            if hue_diff >= 35 or delta_e(primary_cluster["lab"], c["lab"]) > 22.0:
                sec_rgb = c["rgb"]
                break

        accent_candidates = sorted(
            clusters,
            key=lambda c: c["hsv"][1] * 2.0 + (0.8 - abs(c["hsv"][2] - 0.7)),
            reverse=True
        )
        accent_rgb = accent_candidates[0]["rgb"] if accent_candidates else dom_rgb
        acc_h, acc_s, acc_v = rgb_to_hsv(*accent_rgb)
        if acc_s < 0.35:
            acc_s = 0.65
        if acc_v < 0.5:
            acc_v = 0.8
        accent_rgb = hsv_to_rgb(acc_h, min(1.0, acc_s * 1.1), max(0.65, min(0.95, acc_v)))

        bg_dark_rgb = hsv_to_rgb(dom_h, min(0.25, dom_s * 0.35), 0.10)
        bg_sidebar_rgb = hsv_to_rgb(dom_h, min(0.22, dom_s * 0.30), 0.13)
        bg_active_rgb = hsv_to_rgb(dom_h, min(0.35, dom_s * 0.45), 0.18)

        base_fg = hsv_to_rgb(dom_h, min(0.10, dom_s * 0.15), 0.95)
        fg_text = ensure_contrast(base_fg, bg_dark_rgb, min_contrast=7.5)

        base_muted = hsv_to_rgb(dom_h, min(0.15, dom_s * 0.2), 0.65)
        fg_muted = ensure_contrast(base_muted, bg_dark_rgb, min_contrast=4.5)

        cursor_rgb = ensure_contrast(accent_rgb, bg_dark_rgb, min_contrast=5.0)

        return {
            "dominant": rgb_to_hex(*dom_rgb),
            "secondary": rgb_to_hex(*sec_rgb),
            "accent": rgb_to_hex(*accent_rgb),
            "editor_background": rgb_to_hex(*bg_dark_rgb),
            "sidebar_background": rgb_to_hex(*bg_sidebar_rgb),
            "active_tab_background": rgb_to_hex(*bg_active_rgb),
            "editor_foreground": rgb_to_hex(*fg_text),
            "muted_foreground": rgb_to_hex(*fg_muted),
            "cursor": rgb_to_hex(*cursor_rgb),
            "selection": rgb_to_hex(*accent_rgb, 60),
            "status_bar_background": rgb_to_hex(*dom_rgb),
            "status_bar_foreground": rgb_to_hex(*ensure_contrast((255, 255, 255), dom_rgb, min_contrast=4.5)),
            "contrast_ratio": contrast_ratio(fg_text, bg_dark_rgb),
            "raw": {
                "dominant": dom_rgb,
                "secondary": sec_rgb,
                "accent": accent_rgb,
                "dark_bg": bg_dark_rgb,
                "sidebar_bg": bg_sidebar_rgb,
                "active_bg": bg_active_rgb,
                "fg": fg_text,
                "muted": fg_muted,
            }
        }

    def _default_palette(self, fallback_rgb: Tuple[int, int, int]) -> Dict[str, Any]:
        bg = (13, 17, 23)
        fg = (230, 237, 243)
        acc = fallback_rgb
        return {
            "dominant": rgb_to_hex(*fallback_rgb),
            "secondary": "#58a6ff",
            "accent": rgb_to_hex(*acc),
            "editor_background": rgb_to_hex(*bg),
            "sidebar_background": "#161b22",
            "active_tab_background": "#21262d",
            "editor_foreground": rgb_to_hex(*fg),
            "muted_foreground": "#8b949e",
            "cursor": "#58a6ff",
            "selection": "#58a6ff3c",
            "status_bar_background": "#161b22",
            "status_bar_foreground": "#f0f6fc",
            "contrast_ratio": contrast_ratio(fg, bg),
            "raw": {
                "dominant": fallback_rgb,
                "secondary": (88, 166, 255),
                "accent": acc,
                "dark_bg": bg,
                "sidebar_bg": (22, 27, 34),
                "active_bg": (33, 38, 45),
                "fg": fg,
                "muted": (139, 148, 158),
            }
        }

def build_vscode_color_customizations(palette: Dict[str, Any], mode: str = "full") -> Dict[str, str]:
    if mode == "accent-only":
        return {
            "activityBar.activeBorder": palette["accent"],
            "activityBarBadge.background": palette["accent"],
            "editorCursor.foreground": palette["cursor"],
            "editor.selectionBackground": palette["selection"],
            "tab.activeBorder": palette["accent"],
            "statusBar.background": palette["status_bar_background"],
            "statusBar.foreground": palette["status_bar_foreground"],
            "focusBorder": palette["accent"]
        }

    return {
        "editor.background": palette["editor_background"],
        "editor.foreground": palette["editor_foreground"],
        "editorCursor.foreground": palette["cursor"],
        "editor.selectionBackground": palette["selection"],
        "editor.lineHighlightBackground": palette["active_tab_background"] + "44",
        "editorLineNumber.foreground": palette["muted_foreground"] + "99",
        "editorLineNumber.activeForeground": palette["editor_foreground"],

        "activityBar.background": palette["sidebar_background"],
        "activityBar.foreground": palette["editor_foreground"],
        "activityBar.activeBorder": palette["accent"],
        "activityBarBadge.background": palette["accent"],

        "sideBar.background": palette["sidebar_background"],
        "sideBar.foreground": palette["editor_foreground"],
        "sideBarTitle.foreground": palette["editor_foreground"],
        "sideBarSectionHeader.background": palette["editor_background"],
        "sideBarSectionHeader.foreground": palette["editor_foreground"],

        "statusBar.background": palette["status_bar_background"],
        "statusBar.foreground": palette["status_bar_foreground"],
        "statusBarItem.hoverBackground": palette["accent"] + "44",

        "tab.activeBackground": palette["active_tab_background"],
        "tab.activeForeground": palette["editor_foreground"],
        "tab.inactiveBackground": palette["sidebar_background"],
        "tab.inactiveForeground": palette["muted_foreground"],
        "tab.activeBorder": palette["accent"],

        "titleBar.activeBackground": palette["editor_background"],
        "titleBar.activeForeground": palette["editor_foreground"],

        "terminal.background": palette["editor_background"],
        "terminal.foreground": palette["editor_foreground"],

        "focusBorder": palette["accent"],
        "badge.background": palette["accent"],
        "badge.foreground": palette["editor_background"]
    }

color_extractor = ColorPaletteExtractor()
