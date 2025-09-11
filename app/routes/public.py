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
from ..utils.storage import data_dir, legacy_dir, load_ads_cached
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
    return [ad for ad in load_ads_cached() if ad.get("status") == "approved"]

def _sort_by_created_at_desc(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda x: parse_datetime_safe(x.get("created_at", "1970-01-01")),
        reverse=True,
    )

def _find_by_code(code: str) -> Optional[Dict[str, Any]]:
    for ad in load_ads_cached():
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
    سرو فایل‌های آپلود:
      1) ابتدا از UPLOAD_FOLDER (مسیر جدید تاریخ‌محور)
      2) سپس از instance/data/uploads
      3) سپس از <root>/data/uploads (legacy)
    """
    # اول مسیر تنظیم‌شده در کانفیگ
    try:
        base_cfg = current_app.config.get("UPLOAD_FOLDER")
        if base_cfg:
            fp_cfg = os.path.join(base_cfg, filename)
            if os.path.isfile(fp_cfg):
                resp = send_from_directory(base_cfg, filename)
                try:
                    resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
                except Exception:
                    pass
                return resp
    except Exception:
        pass

    # سپس مسیر instance/data/uploads
    upload_roots = (
        os.path.join(data_dir(), "uploads"),
        os.path.join(legacy_dir(), "uploads"),
    )
    for folder in upload_roots:
        fp = os.path.join(folder, filename)
        if os.path.isfile(fp):
            resp = send_from_directory(folder, filename)
            try:
                resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
            except Exception:
                pass
            return resp
    abort(404, description="File not found")

@main_bp.route("/search", endpoint="search_page")
def search_page():
    """
    صفحهٔ جستجو با فیلترها و مرتب‌سازی واحد (نتایج و لیست کامل)
    پارامترها: q, category, min_price, max_price, min_size, max_size, sort
    """
    # ورودی‌ها
    q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip()
    if category not in CATEGORY_MAP:
        category = ""

    def _to_int_safe(v):
        try:
            return int(str(v).replace(",", "").strip())
        except Exception:
            return None

    min_price = _to_int_safe(request.args.get("min_price"))
    max_price = _to_int_safe(request.args.get("max_price"))
    min_size  = _to_int_safe(request.args.get("min_size"))
    max_size  = _to_int_safe(request.args.get("max_size"))
    sort      = (request.args.get("sort") or "newest").strip()

    # استخر کامل برای بخش «همه آگهی‌ها»
    all_pool = _sort_by_created_at_desc(_get_approved_ads())

    # اعمال فیلترها برای نتایج
    results = all_pool
    if category:
        results = [ad for ad in results if (ad.get("category", "") == category)]
    if min_price is not None:
        results = [ad for ad in results if _to_int(ad.get("price_total"), 0) >= min_price]
    if max_price is not None:
        results = [ad for ad in results if _to_int(ad.get("price_total"), 0) <= max_price]
    if min_size is not None:
        results = [ad for ad in results if _to_int(ad.get("size"), 0) >= min_size]
    if max_size is not None:
        results = [ad for ad in results if _to_int(ad.get("size"), 0) <= max_size]
    if q:
        def _hit(ad):
            title = (ad.get("title") or "").lower()
            loc   = (ad.get("location") or "").lower()
            desc  = (ad.get("description") or "").lower()
            code  = str(ad.get("code") or "")
            return (q in title) or (q in loc) or (q in desc) or (q == code.lower())
        results = [ad for ad in results if _hit(ad)]

    # مرتب‌سازی
    if sort == "price_asc":
        results.sort(key=lambda x: _to_int(x.get("price_total"), 0) or 0)
    elif sort == "size_desc":
        results.sort(key=lambda x: _to_int(x.get("size"), 0) or 0, reverse=True)
    else:
        results = _sort_by_created_at_desc(results)

    return render_template(
        "search.html",
        lands=results,
        all_lands=all_pool,
        category=category,
        CATEGORY_MAP=CATEGORY_MAP,
        brand="وینور",
        domain="vinor.ir",
    )

@main_bp.route("/search-results", endpoint="search_results")
def search_results():
    """
    مسیر قدیمی → هدایت به /search با همان پارامترها (یکپارچه‌سازی تجربه)
    """
    try:
        qs = request.query_string.decode("utf-8") if request.query_string else ""
    except Exception:
        qs = ""
    target = url_for("main.search_page")
    if qs:
        target = f"{target}?{qs}"
    return redirect(target)

# -------------------------
# API: لیست آگهی‌های تأییدشده (برای کلاینت فرانت/صفحه علاقه‌مندی)
# -------------------------
@main_bp.get("/api/lands/approved")
def api_lands_approved():
    try:
        items = _sort_by_created_at_desc(_get_approved_ads())
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

        # ETag: تعداد + آخرین created_at (با فرض sort desc)
        last_dt = (items[0].get("created_at") if items else "") or ""
        etag_val = f"v-{len(items)}-{last_dt}"

        inm = request.headers.get("If-None-Match")
        if inm and inm == etag_val:
            resp = current_app.response_class(status=304)
            resp.set_etag(etag_val)
            resp.headers["Cache-Control"] = "public, max-age=60"
            return resp

        resp = current_app.response_class(
            response=current_app.json.dumps({"ok": True, "items": data}, ensure_ascii=False),
            status=200,
            mimetype="application/json; charset=utf-8",
        )
        resp.set_etag(etag_val)
        resp.headers["Cache-Control"] = "public, max-age=60"
        return resp
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
