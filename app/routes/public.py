# app/routes/public.py
import os
from typing import Any, Dict, List, Optional
from flask import render_template, send_from_directory, request, abort
from . import main_bp
from ..utils.storage import data_dir, legacy_dir, load_ads
from ..utils.dates import parse_datetime_safe
from ..constants import CATEGORY_MAP

# -------------------------
# Helpers
# -------------------------
def _to_int(x, default: int = 0) -> int:
    try:
        # گاهی مقادیر رشته‌ای با جداکننده یا اعشار می‌آیند
        return int(float(str(x).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default

def _to_float(x, default: float = 0.0) -> float:
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return default

def _compute_price_per_meter(land: Dict[str, Any]) -> Optional[int]:
    """
    اگر price_per_meter در داده نبود، از price و area محاسبه می‌شود.
    اگر هر کدام نامعتبر باشند، None برمی‌گردد تا قالب بتواند امن نمایش دهد.
    """
    if land.get("price_per_meter") not in (None, "", 0, "0"):
        # اگر مقدار معتبر موجود است همان را برگردان
        return _to_int(land.get("price_per_meter"), default=None)  # type: ignore

    price = _to_int(land.get("price"), default=0)
    area = _to_float(land.get("area"), default=0.0)
    if price > 0 and area > 0:
        return int(round(price / area))
    return None

def _get_approved_ads() -> List[Dict[str, Any]]:
    return [ad for ad in load_ads() if ad.get("status") == "approved"]

def _sort_by_created_at_desc(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda x: parse_datetime_safe(x.get("created_at", "1970-01-01")),
        reverse=True,
    )

def _find_by_code(code: str) -> Optional[Dict[str, Any]]:
    for ad in load_ads():
        if ad.get("code") == code:
            return ad
    return None

# -------------------------
# Routes
# -------------------------
@main_bp.route("/")
def index():
    lands = _sort_by_created_at_desc(_get_approved_ads())
    return render_template("index.html", lands=lands, CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route("/land/<code>")
def land_detail(code):
    land = _find_by_code(code)
    if not land:
        # 404 تمیز
        abort(404, description="آگهی مورد نظر پیدا نشد.")

    # محاسبه و تزریق قیمت متری در صورت نبود
    ppm = _compute_price_per_meter(land)
    land["price_per_meter"] = ppm

    return render_template("land_detail.html", land=land, CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """
    فایل‌های آپلود را از دو محل data و legacy سرو می‌کند.
    """
    upload_roots = (
        os.path.join(data_dir(), "uploads"),
        os.path.join(legacy_dir(), "uploads"),
    )
    for folder in upload_roots:
        fp = os.path.join(folder, filename)
        if os.path.isfile(fp):
            # اگر خواستی: cache_timeout را هم تنظیم کن
            return send_from_directory(folder, filename)
    abort(404, description="File not found")

@main_bp.route("/search")
def search_page():
    active_category = (request.args.get("category") or "").strip()
    if active_category not in CATEGORY_MAP:
        active_category = ""

    ads = _get_approved_ads()
    if active_category:
        ads = [ad for ad in ads if (ad.get("category", "") == active_category)]

    ads = _sort_by_created_at_desc(ads)
    return render_template(
        "search.html",
        ads=ads,
        category=active_category,
        CATEGORY_MAP=CATEGORY_MAP,
    )

@main_bp.route("/search-results")
def search_results():
    q = (request.args.get("q", "") or "").strip().lower()
    pool = _get_approved_ads()
    if q:
        results = []
        for ad in pool:
            title = (ad.get("title") or "").lower()
            loc = (ad.get("location") or "").lower()
            desc = (ad.get("description") or "").lower()
            if q in title or q in loc or q in desc:
                results.append(ad)
    else:
        results = pool

    results = _sort_by_created_at_desc(results)
    return render_template(
        "search_results.html",
        results=results,
        query=q,
        CATEGORY_MAP=CATEGORY_MAP,
    )

@main_bp.route("/city")
def city_select():
    return render_template("city_select.html")
