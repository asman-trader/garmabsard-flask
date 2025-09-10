# app/routes/public.py
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

from flask import (
    render_template, send_from_directory, request, abort,
    redirect, url_for, session, make_response, current_app
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
    فقط به اندپوینت موجود ارجاع می‌دهد تا BuildError رخ ندهد.
    """
    try:
        return url_for("main.login")  # از auth.py
    except Exception:
        return "/login"

# -------------------------
# Context (برای استفادهٔ ساده در تمام قالب‌ها)
# -------------------------
@main_bp.app_context_processor
def inject_vinor_globals():
    """
    متغیرهای عمومیِ وینور برای استفاده در تمپلیت‌ها
    """
    return {
        "VINOR_IS_LOGGED_IN": bool(session.get("user_id")),
        "VINOR_LOGIN_URL": url_for("main.login"),
        "VINOR_HOME_URL": url_for("main.app_home"),
        "VINOR_BRAND": "وینور",
        "VINOR_DOMAIN": "vinor.ir",
    }

# -------------------------
# Routes
# -------------------------

@main_bp.route("/", endpoint="index")
def index():
    """
    لندینگ وینور (Vinor) – فقط برای اولین بار.
    اگر کاربر لاگین باشد، مستقیم به /app می‌رود.
    """
    if session.get("user_id"):
        return redirect(url_for("main.app_home"))
    return render_template("landing.html", brand="وینور", domain="vinor.ir")

@main_bp.route("/start", endpoint="start")
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

@main_bp.route("/app", endpoint="app_home")
def app_home():
    """
    خانه اپ وینور (پس از ورود)
    فهرست آگهی‌های تأییدشده به ترتیب نزولی تاریخ.
    """
    if not session.get("user_id"):
        return redirect(_login_url_fallback())
    lands = _sort_by_created_at_desc(_get_approved_ads())
    return render_template(
        "index.html",
        lands=lands,
        CATEGORY_MAP=CATEGORY_MAP,
        brand="وینور",
        domain="vinor.ir",
    )

@main_bp.route("/land/<code>", endpoint="land_detail")
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

    return render_template(
        "land_detail.html",
        land=land,
        CATEGORY_MAP=CATEGORY_MAP,
        brand="وینور",
        domain="vinor.ir",
    )

@main_bp.route("/uploads/<path:filename>", endpoint="uploaded_file")
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

@main_bp.route("/search", endpoint="search_page")
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

@main_bp.route("/search-results", endpoint="search_results")
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

# -------------------------
# API: لیست آگهی‌های تأییدشده (برای کلاینت فرانت/صفحه علاقه‌مندی)
# -------------------------
@main_bp.get("/api/lands/approved")
def api_lands_approved():
    try:
        items = _sort_by_created_at_desc(_get_approved_ads())
        # حداقل فیلدهای مورد نیاز صفحه علاقه‌مندی
        data = [
            {
                "code": x.get("code"),
                "title": x.get("title"),
                "size": x.get("size"),
                "location": x.get("location"),
                "price_total": x.get("price_total"),
                "images": x.get("images") or [],
            }
            for x in items
        ]
        return {"ok": True, "items": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@main_bp.route("/city", endpoint="city_select")
def city_select():
    """
    انتخاب شهر (برای آینده: شخصی‌سازی نتایج)
    """
    return render_template("city_select.html", brand="وینور", domain="vinor.ir")

# --- About Vinor ---
@main_bp.route("/about")
@main_bp.route("/درباره-ما")
def about():
    """
    صفحهٔ درباره وینور
    هر دو مسیر /about و /درباره-ما به این ویو می‌خورند.
    """
    return render_template(
        "main/about.html",   # اگر فایل را در ریشه templates گذاشتی، بکنش 'about.html'
        brand="وینور",
        domain="vinor.ir",
        current_year=datetime.now().year,
    )

@main_bp.route("/faq")
@main_bp.route("/سوالات-پرتکرار")
def faq():
    """
    صفحهٔ سوالات پرتکرار (FAQ)
    """
    return render_template(
        "main/faq.html",
        brand="وینور",
        domain="vinor.ir",
        current_year=datetime.now().year,
    )

# -------------------------
# PWA Routes (Manifest, SW, Offline)
# -------------------------
## روت‌های PWA در app/__init__.py پیاده‌سازی شده‌اند؛ برای جلوگیری از تداخل حذف شدند.

# -------------------------
# Optional: Web Share Target & Protocol Handler
# -------------------------
@main_bp.route("/share", methods=["GET", "POST"], endpoint="web_share_target")
def web_share_target():
    """
    پذیرش اشتراک‌گذاری وب (title/text/url و فایل‌ها)
    سناریوی ساده: هدایت به ثبت آگهی با پیش‌پر کردن عنوان.
    """
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        text  = (request.form.get("text") or "").strip()
        url_v = (request.form.get("url") or "").strip()
        # TODO: در صورت نیاز، request.files.getlist("files") را پردازش و ذخیره کن

        params = {}
        pretitle = title or text or url_v
        if pretitle:
            params["title"] = pretitle
        target = url_for("main.submit_ad")
        if params:
            target = f"{target}?{urlencode(params)}"
        return redirect(target)

    return redirect(url_for("main.submit_ad"))

@main_bp.route("/open", endpoint="protocol_open")
def protocol_open():
    """
    هندل لینک‌های اختصاصی مانند:
      web+vinor://ad?code=ABC123
    پشتیبانی ساده برای هدایت به جزئیات آگهی.
    """
    uri = request.args.get("uri", "") or ""
    try:
        parsed = urlparse(uri)
        path = (parsed.path or "").lstrip("/")
        qs = parse_qs(parsed.query or "")
        # نمونه: web+vinor://ad?code=XYZ
        if path.lower() in ("ad", "land") and "code" in qs:
            code = (qs.get("code") or [""])[0]
            if code:
                return redirect(url_for("main.land_detail", code=code))
    except Exception:
        pass
    # پیش‌فرض: خانه اپ
    return redirect(url_for("main.app_home"))

# ⚠️ مهم: هیچ مسیر /login /logout /submit-ad در این فایل تعریف نمی‌شود.
#   - /login و /logout در app/routes/auth.py
#   - /submit-ad ریدایرکت در app/routes/ads.py (endpoint='submit_ad_redirect')
