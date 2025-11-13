# app/routes/public.py
import os

from flask import (
    render_template, send_from_directory, request, abort,
    redirect, url_for, session, make_response, current_app, flash
)

from . import main_bp
from ..utils.storage import data_dir, legacy_dir, load_ads_cached
from ..utils.storage import load_express_partners

# ثابت‌ها
FIRST_VISIT_COOKIE = "vinor_first_visit_done"

# -------------------------
# Context (برای استفادهٔ ساده در تمام قالب‌ها)
# -------------------------
@main_bp.app_context_processor
def inject_vinor_globals():
    """
    متغیرهای عمومیِ وینور برای استفاده در تمپلیت‌ها
    """
    # همکار اکسپرس تأییدشده
    try:
        me = str(session.get("user_phone") or "").strip()
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
        "VINOR_HOME_URL": url_for("main.index"),
        "VINOR_BRAND": "وینور",
        "VINOR_DOMAIN": "vinor.ir",
        # نقش‌ها
        "VINOR_IS_EXPRESS_PARTNER": is_express_partner,
    }

# -------------------------
# Routes
# -------------------------

@main_bp.route("/", endpoint="index")
def index():
    """
    لندینگ همکاران وینور – معرفی فرصت‌های همکاری
    """
    return render_template("home/partners.html", brand="وینور", domain="vinor.ir")

@main_bp.route("/partners", endpoint="partners")
def partners():
    """
    لندینگ همکاران وینور – معرفی فرصت‌های همکاری
    """
    return render_template("home/partners.html", brand="وینور", domain="vinor.ir")

@main_bp.route("/start", endpoint="start")
def start():
    """
    CTA لندینگ → ست‌کردن کوکی «اولین بازدید انجام شد»
    سپس به صفحه اصلی (لندینگ همکاران) می‌رویم.
    """
    target = url_for("main.index")
    resp = make_response(redirect(target))
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
        return redirect(url_for('main.index'))
    
    return render_template(
        "lands/express_detail.html",
        land=land,
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

    # سپس مسیر instance/data/uploads و legacy data/uploads
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
    # در نهایت: static/uploads (تصاویر ذخیره‌شده در static)
    try:
        static_root = current_app.static_folder
        # پشتیبانی از هر دو ورودی: 'uploads/...' یا فقط '...'
        candidates = []
        if filename.startswith('uploads/'):
            candidates.append(os.path.join(static_root, filename))
            candidates.append(os.path.join(static_root, filename.lstrip('/')))
        else:
            candidates.append(os.path.join(static_root, 'uploads', filename))
        for cand in candidates:
            if os.path.isfile(cand):
                rel_dir = os.path.dirname(os.path.relpath(cand, static_root))
                fn = os.path.basename(cand)
                resp = send_from_directory(os.path.join(static_root, rel_dir), fn)
                try:
                    resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
                except Exception:
                    pass
                return resp
    except Exception:
        pass
    abort(404, description="File not found")


@main_bp.route("/express-docs/<filename>")
def serve_express_document(filename):
    """سرو کردن مدارک اکسپرس برای کاربران"""
    try:
        docs_dir = os.path.join(current_app.instance_path, 'data', 'express_docs')
        return send_from_directory(docs_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving express document {filename}: {e}")
        abort(404)
