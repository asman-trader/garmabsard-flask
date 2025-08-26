# app/routes/public.py
import os
from typing import Any, Dict, List, Optional
from flask import (
    render_template, send_from_directory, request, abort,
    redirect, url_for, session, make_response
)
from . import main_bp
from ..utils.storage import data_dir, legacy_dir, load_ads
from ..utils.dates import parse_datetime_safe
from ..constants import CATEGORY_MAP

# ثابت‌ها
FIRST_VISIT_COOKIE = "vinor_first_visit_done"


# -------------------------
# Helpers
# -------------------------
def _to_int(x, default: Optional[int] = 0) -> Optional[int]:
    try:
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
    """
    if land.get("price_per_meter") not in (None, "", 0, "0"):
        try:
            return _to_int(land.get("price_per_meter"), default=None)  # type: ignore
        except Exception:
            return None

    price = _to_int(land.get("price"), default=0) or 0
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

def _login_url_fallback() -> str:
    """
    مسیر ورود را به‌صورت امن پیدا می‌کند.
    ابتدا سعی می‌کند اندپوینت‌های رایج را بسازد و اگر نبود، به /login برمی‌گردد.
    """
    for endpoint in ("main.send_otp", "main.login"):
        try:
            return url_for(endpoint)
        except Exception:
            pass
    return "/login"


# -------------------------
# Routes
# -------------------------

@main_bp.route("/")
def index():
    """
    لندینگ وینور (Vinor) – فقط برای اولین بار.
    اگر کاربر لاگین باشد، مستقیم به /app می‌رود.
    """
    if session.get("user_id"):
        return redirect(url_for("main.app_home"))
    return render_template("landing.html", brand="وینور", domain="vinor.ir")


@main_bp.route("/start")
def start():
    """
    CTA لندینگ → ست‌کردن کوکی «اولین بازدید انجام شد»
    سپس:
      - اگر لاگین است → /app
      - اگر لاگین نیست → مسیر ورود (با فالبک امن)
    """
    target = url_for("main.app_home") if session.get("user_id") else _login_url_fallback()
    resp = make_response(redirect(target))
    resp.set_cookie(FIRST_VISIT_COOKIE, "1", max_age=60 * 60 * 24 * 365, samesite="Lax")
    session.permanent = True
    return resp


@main_bp.route("/app")
def app_home():
    """
    خانه اپ وینور (پس از ورود)
    فهرست آگهی‌های تأییدشده به ترتیب نزولی تاریخ.
    """
    if not session.get("user_id"):
        return redirect(_login_url_fallback())
    lands = _sort_by_created_at_desc(_get_approved_ads())
    return render_template("index.html", lands=lands, CATEGORY_MAP=CATEGORY_MAP, brand="وینور", domain="vinor.ir")


@main_bp.route("/land/<code>")
def land_detail(code):
    """
    صفحهٔ جزئیات آگهی
    """
    land = _find_by_code(code)
    if not land:
        abort(404, description="آگهی مورد نظر پیدا نشد.")

    ppm = _compute_price_per_meter(land)
    if ppm is not None:
        land["price_per_meter"] = ppm

    return render_template("land_detail.html", land=land, CATEGORY_MAP=CATEGORY_MAP, brand="وینور", domain="vinor.ir")


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
            return send_from_directory(folder, filename)
    abort(404, description="File not found")


@main_bp.route("/search")
def search_page():
    """
    صفحهٔ جستجو با فیلتر دسته‌بندی
    """
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
        brand="وینور",
        domain="vinor.ir",
    )


@main_bp.route("/search-results")
def search_results():
    """
    نتایج جستجو با تطبیق ساده روی عنوان/موقعیت/توضیحات
    """
    q = (request.args.get("q", "") or "").strip().lower()
    pool = _get_approved_ads()
    if q:
        results: List[Dict[str, Any]] = []
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
        brand="وینور",
        domain="vinor.ir",
    )


@main_bp.route("/city")
def city_select():
    """
    انتخاب شهر (برای آینده: شخصی‌سازی نتایج)
    """
    return render_template("city_select.html", brand="وینور", domain="vinor.ir")

# --- Dev Auth (موقت برای تست) ---
@main_bp.route("/login")
def login():
    # ورود موقت: یک شناسه ساده در سشن ست می‌کنیم تا /app باز شود
    session["user_id"] = "dev-user"
    return redirect(url_for("main.app_home"))

@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))

# --- Submit Ad (placeholder for development) ---
@main_bp.route("/submit-ad")
def submit_ad():
    # فعلاً صفحه‌ی موقت؛ بعداً فرم واقعی ثبت آگهی جایگزین می‌شود
    if not session.get("user_id"):
        return redirect(_login_url_fallback())
    return render_template("submit_ad_placeholder.html", brand="وینور", domain="vinor.ir")
