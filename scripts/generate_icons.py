"""
Generate PWA icon set from a single seed image (sprout) using Pillow.

Usage (PowerShell / CMD):
  python scripts/generate_icons.py --source app/static/icons/icon-512.png --out app/static/icons

Recommended:
  - Provide a high-res transparent PNG (>=1024x1024) of the sprout for best quality
  - The script creates normal and maskable variants
"""
from __future__ import annotations

import argparse
import os
from typing import Tuple

try:
    from PIL import Image
except Exception as e:
    raise SystemExit("Pillow is required. Install first: pip install Pillow")


SIZES = [48, 72, 96, 128, 144, 192, 256, 384, 512]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_source(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img


def crop_quadrant(img: Image.Image, pos: str) -> Image.Image:
    """Crop one quadrant from a 2x2 grid image.

    pos ∈ { 'top-left', 'top-right', 'bottom-left', 'bottom-right' }
    """
    w, h = img.size
    hw, hh = w // 2, h // 2
    if pos == 'top-left':
        box = (0, 0, hw, hh)
    elif pos == 'top-right':
        box = (hw, 0, w, hh)
    elif pos == 'bottom-left':
        box = (0, hh, hw, h)
    elif pos == 'bottom-right':
        box = (hw, hh, w, h)
    else:
        return img
    return img.crop(box)


def resize_contain(img: Image.Image, target: int) -> Image.Image:
    """Resize keeping aspect ratio to fit inside a target square; transparent padding."""
    canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
    src_w, src_h = img.size
    scale = min(target / src_w, target / src_h)
    new_w, new_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    off_x = (target - new_w) // 2
    off_y = (target - new_h) // 2
    canvas.paste(resized, (off_x, off_y), resized)
    return canvas


def make_maskable(img: Image.Image, target: int, safe_ratio: float = 0.8) -> Image.Image:
    """Generate maskable icon by fitting the artwork into the safe area (default 80%)."""
    canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
    safe = int(target * safe_ratio)
    # Center-fit the image within the safe square
    src_w, src_h = img.size
    scale = min(safe / src_w, safe / src_h)
    new_w, new_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    off_x = (target - new_w) // 2
    off_y = (target - new_h) // 2
    canvas.paste(resized, (off_x, off_y), resized)
    return canvas


def generate_all(source_path: str, out_dir: str, crop: str | None = None) -> None:
    ensure_dir(out_dir)
    src = load_source(source_path)
    if crop:
        src = crop_quadrant(src, crop)

    for size in SIZES:
        # Standard icon
        icon = resize_contain(src, size)
        icon.save(os.path.join(out_dir, f"icon-{size}.png"))

        # Maskable icon
        maskable = make_maskable(src, size, safe_ratio=0.78)
        maskable.save(os.path.join(out_dir, f"maskable-{size}.png"))

    print(f"✅ Generated icons in: {out_dir}")


def parse_args() -> Tuple[str, str, str | None]:
    p = argparse.ArgumentParser(description="Generate PWA icons from a single seed image")
    p.add_argument("--source", required=True, help="Path to high-res source PNG (sprout)")
    p.add_argument("--out", default="app/static/icons", help="Output directory (default: app/static/icons)")
    p.add_argument("--crop", choices=["top-left", "top-right", "bottom-left", "bottom-right"], help="Crop one quadrant from a 2x2 sheet before resizing")
    a = p.parse_args()
    return a.source, a.out, a.crop


if __name__ == "__main__":
    src, out, crop = parse_args()
    generate_all(src, out, crop)


