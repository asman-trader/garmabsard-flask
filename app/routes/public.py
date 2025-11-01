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
from ..utils.storage import data_dir, legacy_dir, load_ads_cached, load_reports, save_reports
from ..utils.storage import load_consultant_apps, save_consultant_apps, load_consultants, save_consultants
from ..utils.storage import (
    load_express_partner_apps,
    save_express_partner_apps,
    load_express_partners,
    save_express_partners,
    load_partner_notes,
    save_partner_notes,
    load_partner_sales,
    save_partner_sales,
    load_partner_files_meta,
    save_partner_files_meta,
    load_express_assignments,
    load_express_commissions,
)
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
    # همهٔ آگهی‌های تأییدشده (شامل اکسپرس)
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
    # وضعیت‌های نقش/تأیید برای ناوبری هوشمند
    try:
        me = str(session.get("user_phone") or "").strip()
    except Exception:
        me = ""

    # مشاور تأییدشده
    try:
        _consultants = load_consultants()
        is_consultant = any(
            isinstance(c, dict)
            and str(c.get("phone") or "").strip() == me
            and (str(c.get("status") or "").lower() == "approved" or c.get("status") is True)
            for c in (_consultants or [])
        )
    except Exception:
        is_consultant = False

    # همکار اکسپرس تأییدشده
    try:
        _partners = load_express_partners()
        is_express_partner = any(
            isinstance(p, dict)
            and str(p.get("phone") or "").strip() == me
            and (str(p.get("status") or "").lower() == "approved" or p.get("status") is True)
            for p in (_partners or [])
        )
    except Exception:
        is_express_partner = False

    return {
        "VINOR_IS_LOGGED_IN": bool(session.get("user_id")),
        "VINOR_LOGIN_URL": url_for("main.login"),
        "VINOR_HOME_URL": url_for("main.app_home"),
        "VINOR_BRAND": "وینور",
        "VINOR_DOMAIN": "vinor.ir",
        # نقش‌ها
        "VINOR_IS_CONSULTANT": is_consultant,
        "VINOR_IS_EXPRESS_PARTNER": is_express_partner,
    }

# -------------------------
# Routes
# -------------------------

@main_bp.route("/", endpoint="index")
def index():
    """
    لندینگ وینور (Vinor) – معرفی وینور و نصب PWA.
    همیشه محتوای لندینگ را نشان می‌دهد.
    """
    return render_template("home/landing.html", brand="وینور", domain="vinor.ir")

## مسیرهای مشاورین (careers/apply) حذف شدند

## Express Partner routes moved to app/express_partner/routes.py

## مسیر داشبورد مشاور حذف شد

@main_bp.route("/start", endpoint="start")
def start():
    """
    CTA لندینگ → ست‌کردن کوکی «اولین بازدید انجام شد»
    سپس همیشه به /app می‌رویم (مهمان یا لاگین).
    """
    target = url_for("main.app_home")
    resp = make_response(redirect(target))
    resp.set_cookie(FIRST_VISIT_COOKIE, "1", max_age=60 * 60 * 24 * 365, samesite="Lax")
    session.permanent = True
    return resp

@main_bp.route("/app", endpoint="app_home")
def app_home():
    """
    خانه اپ وینور – برای مهمان و کاربر وارد شده.
    فهرست آگهی‌های تأییدشده به ترتیب نزولی تاریخ.
    عملیات نیازمند ورود (ثبت/علاقه‌مندی و ...) همچنان با گارد کلاینت/سرور حفاظت می‌شود.
    """
    lands = _sort_by_created_at_desc(_get_approved_ads())
    
    # Set first visit cookie if not already set
    resp = make_response(render_template(
        "home/index.html",
        lands=lands,
        CATEGORY_MAP=CATEGORY_MAP,
        brand="وینور",
        domain="vinor.ir",
    ))
    
    if not request.cookies.get(FIRST_VISIT_COOKIE):
        resp.set_cookie(FIRST_VISIT_COOKIE, "1", max_age=60 * 60 * 24 * 365, samesite="Lax")
        session.permanent = True
    
    return resp

@main_bp.route("/express/<code>", endpoint="express_detail")
def express_detail(code):
    """
    صفحهٔ جزئیات آگهی اکسپرس
    """
    lands = load_ads_cached()
    land = next((l for l in lands if l.get('code') == code and l.get('is_express', False)), None)
    
    if not land:
        flash('آگهی اکسپرس یافت نشد.', 'warning')
        return redirect(url_for('main.app_home'))
    
    return render_template(
        "lands/express_detail.html",
        land=land,
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
        "lands/land_detail.html",
        land=land,
        CATEGORY_MAP=CATEGORY_MAP,
        brand="وینور",
        domain="vinor.ir",
    )

@main_bp.route("/report/<code>", methods=["GET", "POST"], endpoint="report_ad")
def report_ad(code):
    """
    گزارش آگهی توسط کاربر: ذخیره در reports.json واقع در instance/data
    ساختار هر گزارش: { id, code, reason, details, created_at, status }
    """
    ad = _find_by_code(code)
    if not ad:
        abort(404, description="آگهی یافت نشد")

    if request.method == "POST":
        reason = (request.form.get("reason") or "").strip()
        details = (request.form.get("details") or "").strip()

        items = load_reports()
        if not isinstance(items, list):
            items = []
        new_id = (max([x.get("id", 0) for x in items], default=0) or 0) + 1
        client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or ''
        ua = request.headers.get('User-Agent', '')
        rec = {
            "id": new_id,
            "code": str(code),
            "reason": reason or "unspecified",
            "details": details,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "open",
            "ip": client_ip,
            "ua": ua,
        }
        items.append(rec)
        save_reports(items)
        return redirect(url_for("main.land_detail", code=code, reported=1))

    return render_template(
        "lands/report_ad.html",
        land=ad,
        code=code,
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
    city_param = (request.args.get("city") or "").strip().lower()
    city_multi = []
    try:
        # اگر city به صورت "تهران,ری,ورامین" ارسال شد
        if "," in city_param:
            city_multi = [c.strip() for c in city_param.split(",") if c.strip()]
    except Exception:
        city_multi = []
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
    if city_multi:
        def _city_of(ad):
            c1 = (ad.get("city") or "").strip().lower()
            if c1:
                return c1
            loc = (ad.get("location") or "").strip().lower()
            return loc.split("-")[0].strip() if loc else ""
        results = [ad for ad in results if _city_of(ad) in city_multi]
    elif city_param:
        def _city_of(ad):
            c1 = (ad.get("city") or "").strip().lower()
            if c1:
                return c1
            loc = (ad.get("location") or "").strip().lower()
            # allow formats like "تهران - ..."
            return loc.split("-")[0].strip() if loc else ""
        results = [ad for ad in results if _city_of(ad) == city_param]
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
        "search/search.html",
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

        # Pagination params (offset/limit)
        try:
            offset = max(0, int(request.args.get("offset", 0)))
        except Exception:
            offset = 0
        try:
            limit = int(request.args.get("limit", 24))
        except Exception:
            limit = 24
        if limit < 1:
            limit = 1
        if limit > 60:
            limit = 60

        total = len(items)
        page_items = items[offset: offset + limit]

        data = [
            {
                "code": x.get("code"),
                "title": x.get("title"),
                "size": x.get("size"),
                "location": x.get("location"),
                "price_total": x.get("price_total"),
                "images": x.get("images") or [],
            }
            for x in page_items
        ]

        # ETag only for the first page (offset==0)
        if offset == 0:
            last_dt = (items[0].get("created_at") if items else "") or ""
            etag_val = f"v-{len(items)}-{last_dt}"
            inm = request.headers.get("If-None-Match")
            if inm and inm == etag_val:
                resp = current_app.response_class(status=304)
                resp.set_etag(etag_val)
                resp.headers["Cache-Control"] = "public, max-age=60"
                return resp

            payload = {"ok": True, "items": data, "total": total, "has_more": (offset + len(page_items)) < total}
            resp = current_app.response_class(
                response=current_app.json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json; charset=utf-8",
            )
            resp.set_etag(etag_val)
            resp.headers["Cache-Control"] = "public, max-age=60"
            return resp
        else:
            # For subsequent pages skip ETag/304 handling
            payload = {"ok": True, "items": data, "total": total, "has_more": (offset + len(page_items)) < total}
            return current_app.response_class(
                response=current_app.json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json; charset=utf-8",
            )
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@main_bp.route("/city", endpoint="city_select")
def city_select():
    """
    انتخاب شهر تکی (برای ثبت آگهی)
    """
    return render_template("city/city_select.html", brand="وینور", domain="vinor.ir")

@main_bp.route("/city/multi", endpoint="city_select_multi")
def city_select_multi():
    """
    انتخاب چند استان/شهر (برای فیلتر جستجو)
    """
    return render_template("city/city_select_multi.html", brand="وینور", domain="vinor.ir")

# --- About Vinor ---
@main_bp.route("/درباره-ما")
@main_bp.route("/about")
def about():
    """
    صفحهٔ درباره وینور
    هر دو مسیر /about و /درباره-ما به این ویو می‌خورند.
    """
    # Canonicalize Farsi slug → English
    try:
        if request.path.rstrip("/") == "/درباره-ما":
            return redirect(url_for("main.about"), code=301)
    except Exception:
        pass
    return render_template(
        "main/about.html",   # اگر فایل را در ریشه templates گذاشتی، بکنش 'about.html'
        brand="وینور",
        domain="vinor.ir",
        current_year=datetime.now().year,
    )

@main_bp.route("/سوالات-پرتکرار")
@main_bp.route("/faq")
def faq():
    """
    صفحهٔ سوالات پرتکرار (FAQ)
    """
    # Canonicalize Farsi slug → English
    try:
        if request.path.rstrip("/") == "/سوالات-پرتکرار":
            return redirect(url_for("main.faq"), code=301)
    except Exception:
        pass
    return render_template(
        "main/faq.html",
        brand="وینور",
        domain="vinor.ir",
        current_year=datetime.now().year,
    )

# --- Unified Help page ---
@main_bp.route("/راهنما")
@main_bp.route("/help", endpoint="help")
def help_page():
    # Canonicalize Farsi slug → English
    try:
        if request.path.rstrip("/") == "/راهنما":
            return redirect(url_for("main.help"), code=301)
    except Exception:
        pass
    return render_template(
        "main/help.html",
        brand="وینور",
        domain="vinor.ir",
        current_year=datetime.now().year,
    )

# --- Buying Guides ---
@main_bp.route("/راهنمای-خرید-امن")
@main_bp.route("/guide/safe-buy", endpoint="buy_safe")
def buy_safe():
    """
    صفحهٔ راهنمای خرید امن در وینور
    """
    # Canonicalize Farsi slug → English
    try:
        if request.path.rstrip("/") == "/راهنمای-خرید-امن":
            return redirect(url_for("main.buy_safe"), code=301)
    except Exception:
        pass
    return render_template(
        "main/buy_safe.html",
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

@main_bp.route("/express-docs/<filename>")
def serve_express_document(filename):
    """سرو کردن مدارک اکسپرس برای کاربران"""
    try:
        docs_dir = os.path.join(current_app.instance_path, 'data', 'express_docs')
        return send_from_directory(docs_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving express document {filename}: {e}")
        abort(404)

# ⚠️ مهم: هیچ مسیر /login /logout /submit-ad در این فایل تعریف نمی‌شود.
#   - /login و /logout در app/routes/auth.py
#   - /submit-ad ریدایرکت در app/routes/ads.py (endpoint='submit_ad_redirect')
