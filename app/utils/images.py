"""
Image helper utilities for Vinor.

- Normalize upload URLs to absolute `/uploads/...` form
- Generate WebP variants (thumb/full) with cached files under `__variants__/`
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

from flask import current_app

try:
    from PIL import Image, ImageOps  # type: ignore

    _PIL_OK = True
except Exception:  # pragma: no cover - fallback when Pillow is missing
    _PIL_OK = False

THUMB_WIDTH = 400
THUMB_QUALITY = 60
FULL_WIDTH = 1400
FULL_QUALITY = 80
DEFAULT_FMT = "WEBP"


def normalize_upload_url(value: Optional[str]) -> str:
    """
    Convert stored value to URL that can be requested from the client.
    - External URLs are returned as-is.
    - `uploads/...` or bare filenames are prefixed with `/uploads/`.
    """
    if not value:
        return ""
    s = str(value).strip()
    if "://" in s:
        return s
    if s.startswith("/uploads/"):
        return s
    if s.startswith("uploads/"):
        return "/uploads/" + s[8:]
    if s.startswith("/static/"):
        return s
    # date-based paths like 2025/08/...
    if s.startswith("/"):
        return "/uploads" + s
    return "/uploads/" + s


def build_variant_url(base_url: str, width: int, quality: int, fmt: str = "webp", variant: str = "") -> str:
    if not base_url:
        return ""
    params = f"w={width}&q={quality}&fmt={fmt}"
    if variant:
        params += f"&variant={variant}"
    joiner = "&" if "?" in base_url else "?"
    return f"{base_url}{joiner}{params}"


def _safe_open_image(src_path: str) -> Optional[Image.Image]:
    if not _PIL_OK:
        return None
    try:
        im = Image.open(src_path)
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        return im
    except Exception:
        return None


def _variant_paths(upload_root: str, rel_path: str, folder: str, fmt: str = "webp") -> Tuple[str, str]:
    rel_path = os.path.normpath(rel_path).replace("\\", "/")
    rel_no_ext, _ = os.path.splitext(rel_path)
    variant_rel = os.path.join("__variants__", folder, f"{rel_no_ext}.{fmt}").replace("\\", "/")
    variant_abs = os.path.join(upload_root, variant_rel)
    return variant_rel, variant_abs


def generate_variant(upload_root: str, rel_path: str, width: int, quality: int, folder: str, fmt: str = DEFAULT_FMT) -> Optional[str]:
    """
    Create (or return existing) variant file and return its *relative* path from upload root.
    """
    if not upload_root or not rel_path or not _PIL_OK or width <= 0:
        return None

    src_abs = os.path.join(upload_root, rel_path)
    if not os.path.isfile(src_abs):
        return None

    rel_variant, abs_variant = _variant_paths(upload_root, rel_path, folder, fmt.lower())
    os.makedirs(os.path.dirname(abs_variant), exist_ok=True)

    if os.path.isfile(abs_variant):
        return rel_variant

    im = _safe_open_image(src_abs)
    if im is None:
        return None

    try:
        im.thumbnail((width, width * 10_000), Image.LANCZOS)
        im.save(abs_variant, format=fmt.upper(), quality=quality, optimize=True)
        return rel_variant
    except Exception:
        try:
            # Clean up partial files on failure
            if os.path.isfile(abs_variant):
                os.remove(abs_variant)
        except Exception:
            pass
        return None


def generate_thumb_and_full(upload_root: str, rel_path: str) -> Dict[str, Optional[str]]:
    """
    Generate both thumb and full variants, returning their relative paths.
    Keys: thumb_rel, full_rel
    """
    return {
        "thumb_rel": generate_variant(upload_root, rel_path, THUMB_WIDTH, THUMB_QUALITY, "thumb", DEFAULT_FMT),
        "full_rel": generate_variant(upload_root, rel_path, FULL_WIDTH, FULL_QUALITY, "full", DEFAULT_FMT),
    }


def variant_headers_for_width(width: int) -> str:
    """
    Cache policy based on requested width.
    - thumb (<=450px): longer cache
    - full (>=1200px): medium cache
    - otherwise: default 1 day
    """
    if width <= 450:
        return "public, max-age=2592000, stale-while-revalidate=604800"  # 30d / 7d
    if width >= 1200:
        return "public, max-age=604800, stale-while-revalidate=604800"   # 7d / 7d
    return "public, max-age=86400, stale-while-revalidate=86400"


def prepare_variants_dict(url: str) -> Dict[str, str]:
    """
    Convenience helper to build thumb/full URLs with query parameters for a given base upload URL.
    """
    base = normalize_upload_url(url)
    return {
        "raw": base,
        "thumb": build_variant_url(base, THUMB_WIDTH, THUMB_QUALITY, "webp", "thumb") if base else "",
        "full": build_variant_url(base, FULL_WIDTH, FULL_QUALITY, "webp", "full") if base else "",
    }

