"""Pipeline de traitement d'image non destructif avec mise en cache du rendu."""

import hashlib
import json
import logging
import math
import random
from pathlib import Path
from typing import Dict, Any
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw

from app.core.config import PROCESSED_DIR

logger = logging.getLogger("wallpapermaison.adjuster")

class ImageAdjuster:
    """Applique une série de transformations et filtres non destructifs à une image."""

    def __init__(self) -> None:
        self.output_dir = PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_output_filename(self, src_path: Path, adj: Dict[str, Any]) -> Path:
        """Génère un nom de fichier unique basé sur le fichier source et ses réglages."""
        adj_str = json.dumps(adj, sort_keys=True)
        key = f"{src_path.resolve()}_{src_path.stat().st_mtime}_{adj_str}"
        file_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return self.output_dir / f"adj_{file_hash}.jpg"

    def apply_adjustments(self, src_path: Path, adj: Dict[str, Any], force: bool = False) -> str:
        """Applique les réglages et retourne le chemin absolu du fichier traité."""
        if not src_path.exists():
            return str(src_path)

        out_path = self.get_output_filename(src_path, adj)
        if out_path.exists() and not force:
            return str(out_path)

        try:
            with Image.open(src_path) as img:
                # Travail en mode RGB
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # 1. Orientation & Géométrie
                rotate = int(adj.get("rotate", 0))
                if rotate % 360 != 0:
                    img = img.rotate(rotate, expand=True)

                if adj.get("flip_h", False):
                    img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

                if adj.get("flip_v", False):
                    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

                # 2. Crop
                cx = float(adj.get("crop_x", 0.0))
                cy = float(adj.get("crop_y", 0.0))
                cw = float(adj.get("crop_w", 1.0))
                ch = float(adj.get("crop_h", 1.0))
                if cw < 1.0 or ch < 1.0 or cx > 0.0 or cy > 0.0:
                    w, h = img.size
                    box = (
                        int(cx * w),
                        int(cy * h),
                        int(min(w, (cx + cw) * w)),
                        int(min(h, (cy + ch) * h))
                    )
                    if box[2] > box[0] and box[3] > box[1]:
                        img = img.crop(box)

                # 3. Noir et Blanc & Sepia
                if adj.get("black_and_white", False):
                    img = ImageOps.grayscale(img).convert("RGB")
                elif adj.get("sepia", False):
                    img = self._apply_sepia(img)

                # 4. Luminosité & Exposition
                brightness = float(adj.get("brightness", 1.0))
                exposure = float(adj.get("exposure", 0.0))
                total_brightness = max(0.1, brightness * (1.0 + exposure))
                if total_brightness != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(total_brightness)

                # 5. Contraste
                contrast = float(adj.get("contrast", 1.0))
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)

                # 6. Saturation & Vibrance
                saturation = float(adj.get("saturation", 1.0))
                vibrance = float(adj.get("vibrance", 1.0))
                total_color = max(0.0, saturation * vibrance)
                if total_color != 1.0 and not adj.get("black_and_white", False):
                    img = ImageEnhance.Color(img).enhance(total_color)

                # 7. Netteté
                sharpness = float(adj.get("sharpness", 0.0))
                if sharpness > 0.0:
                    factor = 1.0 + (sharpness * 1.5)
                    img = ImageEnhance.Sharpness(img).enhance(factor)

                # 8. Flou (Blur)
                blur = float(adj.get("blur", 0.0))
                if blur > 0.0:
                    radius = blur * 10.0
                    img = img.filter(ImageFilter.GaussianBlur(radius=radius))

                # 9. Température et Teinte
                temp = float(adj.get("temperature", 0.0)) # -1.0 (froid) à +1.0 (chaud)
                tint = float(adj.get("tint", 0.0))        # -1.0 (vert) à +1.0 (magenta)
                if temp != 0.0 or tint != 0.0:
                    img = self._apply_temperature_tint(img, temp, tint)

                # 10. Vignettage
                vignette = float(adj.get("vignette", 0.0))
                if vignette > 0.0:
                    img = self._apply_vignette(img, vignette)

                # Sauvegarde du résultat
                img.save(out_path, "JPEG", quality=92, optimize=True)
                logger.info("Image traitée sauvegardée dans le cache: %s", out_path.name)
                return str(out_path)

        except Exception as e:
            logger.error("Erreur lors de l'application des réglages pour %s: %s", src_path, e)
            return str(src_path)

    def _apply_sepia(self, img: Image.Image) -> Image.Image:
        """Applique une teinte sépia douce et élégante."""
        gray = ImageOps.grayscale(img)
        # Teinte sépia (240, 200, 145)
        sepia = ImageOps.colorize(gray, black="#201812", white="#f3e5ab", mid="#9b7653")
        return sepia.convert("RGB")

    def _apply_temperature_tint(self, img: Image.Image, temp: float, tint: float) -> Image.Image:
        """Ajuste la balance thermique (rouge/bleu) et la teinte (vert/magenta)."""
        r, g, b = img.split()
        # Température: augmente le rouge si positif, le bleu si négatif
        if temp > 0:
            r = ImageEnhance.Brightness(r).enhance(1.0 + (temp * 0.3))
            b = ImageEnhance.Brightness(b).enhance(max(0.2, 1.0 - (temp * 0.3)))
        elif temp < 0:
            b = ImageEnhance.Brightness(b).enhance(1.0 + (abs(temp) * 0.3))
            r = ImageEnhance.Brightness(r).enhance(max(0.2, 1.0 - (abs(temp) * 0.3)))

        # Teinte: augmente magenta si positif, vert si négatif
        if tint > 0:
            r = ImageEnhance.Brightness(r).enhance(1.0 + (tint * 0.15))
            b = ImageEnhance.Brightness(b).enhance(1.0 + (tint * 0.15))
            g = ImageEnhance.Brightness(g).enhance(max(0.2, 1.0 - (tint * 0.2)))
        elif tint < 0:
            g = ImageEnhance.Brightness(g).enhance(1.0 + (abs(tint) * 0.2))

        return Image.merge("RGB", (r, g, b))

    def _apply_vignette(self, img: Image.Image, intensity: float) -> Image.Image:
        """Applique un vignettage dégradé radial élégant."""
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)

        # Tracé d'ellipses concentriques avec dégradé
        steps = 40
        max_rad = math.sqrt((w / 2) ** 2 + (h / 2) ** 2)
        cx, cy = w / 2, h / 2

        for i in range(steps):
            ratio = i / steps
            # Seuil de départ du vignettage au centre
            if ratio < (1.0 - (intensity * 0.6)):
                continue
            rad_x = (w / 2) * (ratio)
            rad_y = (h / 2) * (ratio)
            alpha = int(255 * ((ratio - (1.0 - (intensity * 0.6))) / (intensity * 0.6)))
            draw.ellipse([cx - rad_x, cy - rad_y, cx + rad_x, cy + rad_y], fill=min(255, alpha))

        # Masque inversé pour assombrir les bords
        black_layer = Image.new("RGB", (w, h), (0, 0, 0))
        img = Image.composite(black_layer, img, mask)
        return img

image_adjuster = ImageAdjuster()
