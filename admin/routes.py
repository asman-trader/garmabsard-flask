# app/admin/routes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import List, Dict, Any, Optional

from flask import (
    render_template, request, redirect, url_for,
    session, current_app, flash, abort, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename


# اگر CSRFProtect در app factory فعال است، فقط روی روت لاگین موقتاً معاف می‌کنیم
try:
    from flask_wtf.csrf import csrf  # LocalProxy
except Exception:
    csrf = None

# -----------------------------------------------------------------------------
# اعلان‌ها (Vinor Notifications)
# -----------------------------------------------------------------------------
from app.services.notifications import add_notification

# -----------------------------------------------------------------------------
# Express Listings Management
# -----------------------------------------------------------------------------
def _get_express_docs_dir():
    """مسیر ذخیره مدارک اکسپرس"""
    docs_dir = os.path.join(current_app.instance_path, 'data', 'express_docs')
    os.makedirs(docs_dir, exist_ok=True)
    return docs_dir

def _save_express_document(file, land_code):
    """ذخیره مدارک اکسپرس"""
    if not file or not file.filename:
        return None
    
    docs_dir = _get_express_docs_dir()
    # اضافه کردن timestamp برای جلوگیری از تداخل نام فایل
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    filename = secure_filename(f"{land_code}_{timestamp}_{file.filename}")
    file_path = os.path.join(docs_dir, filename)
    file.save(file_path)
    return filename
from app.api.push import _load_subs, _send_one
from app.services.sms import send_sms_template
from app.utils.storage import load_users, load_reports, save_reports, save_ads
from app.utils.storage import (
    load_express_partner_apps,
    save_express_partner_apps,
    load_express_partners,
    save_express_partners,
    load_express_assignments,
    save_express_assignments,
    load_express_commissions,
    save_express_commissions,
    load_partner_files_meta,
    save_partner_files_meta,
    load_active_cities,
    save_active_cities,
)
from app.services.notifications import add_notification

def _ad_owner_id(ad: Dict[str, Any]) -> Optional[str]:
    """شناسه کاربر آگهی‌دهنده از فیلدهای رایج."""
    return ad.get('owner') or ad.get('user_phone') or ad.get('phone')

def _safe_action_url(ad_code: str) -> str:
    """اگر روت جزئیات آگهی نبود، به آگهی‌های من برگرد."""
    try:
        return url_for('main.land_detail', code=ad_code)
    except Exception:
        try:
            return url_for('main.my_lands')
        except Exception:
            return '/my-lands'

def notify_status_change(ad: Dict[str, Any], status: str, reason: Optional[str] = None):
    """ارسال اعلان براساس تغییر وضعیت."""
    uid = _ad_owner_id(ad)
    if not uid:
        return
    code = str(ad.get('code') or '')
    action_url = _safe_action_url(code)

    if status == 'approved':
        add_notification(
            user_id=uid,
            title="آگهی شما تأیید شد",
            body="آگهی شما در وینور منتشر شد.",
            ntype="success",
            ad_id=code,
            action_url=action_url
        )
        # تلاش برای ارسال Web Push به تمام مشترکین
        try:
            payload = {
                'title': 'آگهی شما تأیید شد',
                'body': 'آگهی شما در وینور منتشر شد.',
                'url': action_url,
                'icon': '/static/icons/icon-192.png',
                'badge': '/static/icons/monochrome-192.png',
                'tag': 'vinor-ad-approved'
            }
            for s in (_load_subs() or []):
                _send_one(s, payload)
        except Exception:
            pass
    elif status == 'rejected':
        body = "آگهی شما نیاز به اصلاح دارد."
        if reason:
            body += f" دلیل: {reason}"
        add_notification(
            user_id=uid,
            title="آگهی شما رد شد / نیاز به اصلاح",
            body=body,
            ntype="warning",
            ad_id=code,
            action_url=action_url
        )
        try:
            payload = {
                'title': 'آگهی شما رد شد / نیاز به اصلاح',
                'body': body,
                'url': action_url,
                'icon': '/static/icons/icon-192.png',
                'badge': '/static/icons/monochrome-192.png',
                'tag': 'vinor-ad-rejected'
            }
            for s in (_load_subs() or []):
                _send_one(s, payload)
        except Exception:
            pass
    elif status == 'expired':
        add_notification(
            user_id=uid,
            title="آگهی شما منقضی شد",
            body="برای تمدید از بخش آگهی‌های من اقدام کنید.",
            ntype="info",
            ad_id=code,
            action_url=url_for('main.my_lands')
        )
        try:
            payload = {
                'title': 'آگهی شما منقضی شد',
                'body': 'برای تمدید از بخش آگهی‌های من اقدام کنید.',
                'url': url_for('main.my_lands'),
                'icon': '/static/icons/icon-192.png',
                'badge': '/static/icons/monochrome-192.png',
                'tag': 'vinor-ad-expired'
            }
            for s in (_load_subs() or []):
                _send_one(s, payload)
        except Exception:
            pass

def notify_admin_edit(ad: Dict[str, Any]):
    """اعلان بعد از ویرایش توسط ادمین."""
    uid = _ad_owner_id(ad)
    if not uid:
        return
    code = str(ad.get('code') or '')
    add_notification(
        user_id=uid,
        title="ویرایش آگهی انجام شد",
        body="تغییرات آگهی شما توسط پشتیبانی وینور اعمال شد.",
        ntype="info",
        ad_id=code,
        action_url=_safe_action_url(code)
    )
    try:
        payload = {
            'title': 'ویرایش آگهی انجام شد',
            'body': 'تغییرات آگهی شما توسط پشتیبانی وینور اعمال شد.',
            'url': _safe_action_url(code),
            'icon': '/static/icons/icon-192.png',
            'badge': '/static/icons/monochrome-192.png',
            'tag': 'vinor-ad-edited'
        }
        for s in (_load_subs() or []):
            _send_one(s, payload)
    except Exception:
        pass

def notify_admin_create(ad: Dict[str, Any]):
    """اعلان بعد از ثبت آگهی توسط ادمین (در صورت وجود صاحب)."""
    uid = _ad_owner_id(ad)
    if not uid:
        return
    code = str(ad.get('code') or '')
    st = str(ad.get('status') or 'pending')
    if st == 'approved':
        title, body, ntype = "آگهی شما منتشر شد", "آگهی شما توسط پشتیبانی وینور ثبت و منتشر شد.", "success"
    else:
        title, body, ntype = "آگهی شما ثبت شد", "وضعیت: در انتظار تأیید.", "status"
    add_notification(
        user_id=uid, title=title, body=body, ntype=ntype,
        ad_id=code, action_url=_safe_action_url(code)
    )
    try:
        payload = {
            'title': title,
            'body': body,
            'url': _safe_action_url(code),
            'icon': '/static/icons/icon-192.png',
            'badge': '/static/icons/monochrome-192.png',
            'tag': 'vinor-ad-created'
        }
        for s in (_load_subs() or []):
            _send_one(s, payload)
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Blueprint (defined centrally)
# -----------------------------------------------------------------------------
try:
    from .blueprint import admin_bp
except Exception:
    from flask import Blueprint
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

# -----------------------------------------------------------------------------
# پیکربندی ساده ادمین (برای شروع)
# -----------------------------------------------------------------------------
# نکته امنیتی: پس از استقرار، این‌ها را از config/DB بخوانید یا به سیستم کاربران/نقش‌ها مهاجرت کنید.
ADMIN_USERNAME = 'masood1528014@gmail.com'
ADMIN_PASSWORD = 'm430128185'

# پیش‌فرض صفحه‌بندی برای گرید 3 ستونه
PER_PAGE_DEFAULT = 9


# -----------------------------------------------------------------------------
# مسیرهای فایل‌ها (instance/data با fallback)
# -----------------------------------------------------------------------------
def _settings_path() -> str:
    return current_app.config.get(
        'SETTINGS_FILE',
        os.path.join(current_app.instance_path, 'data', 'settings.json')
    )

def _lands_path() -> str:
    primary = current_app.config.get(
        "LANDS_FILE",
        os.path.join(current_app.instance_path, "data", "lands.json")
    )
    if os.path.exists(primary):
        return primary
    # fallback: مسیر قدیمی داخل app/data/lands.json
    fallback = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "data", "lands.json")
    return fallback


# ریشه آپلود تصاویر (static/uploads)
def _uploads_root() -> str:
    return os.path.join(current_app.static_folder, 'uploads')

# -----------------------------------------------------------------------------
# توابع کمکی JSON
# -----------------------------------------------------------------------------
def load_json(path: str):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data if isinstance(data, (list, dict)) else []
            except json.JSONDecodeError:
                return []
    return []

def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -----------------------------------------------------------------------------
# تنظیمات سیستم
# -----------------------------------------------------------------------------
def _default_settings() -> Dict[str, Any]:
    return {
        'approval_method': 'manual',
        'ad_expiry_days': 30,  # 0 = نامحدود
        'show_submit_button': True,
    }

def get_settings() -> Dict[str, Any]:
    settings_file = _settings_path()
    data: Dict[str, Any] = {}
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f) or {}
            except json.JSONDecodeError:
                data = {}
    defaults = _default_settings()
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data

def save_settings(new_data: Dict[str, Any]) -> None:
    data = get_settings()
    data.update({k: v for k, v in new_data.items() if v is not None})
    save_json(_settings_path(), data)

# -----------------------------------------------------------------------------
# تاریخ/زمان
# -----------------------------------------------------------------------------
def utcnow() -> datetime:
    return datetime.utcnow()

def iso_z(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"

def parse_iso_to_naive_utc(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        return dt.replace(tzinfo=None)
    except Exception:
        return None

# -----------------------------------------------------------------------------
# کمکی‌های لیست آگهی + متای انقضا
# -----------------------------------------------------------------------------
def counts_by_status(lands: List[Dict[str, Any]]):
    pending = sum(1 for l in lands if str(l.get("status", "pending")) == "pending")
    approved = sum(1 for l in lands if str(l.get("status")) == "approved")
    rejected = sum(1 for l in lands if str(l.get("status")) == "rejected")
    return pending, approved, rejected

def paginate(items: List[Any], page: int, per_page: int):
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "total": total,
    }

def find_by_code(lands: List[Dict[str, Any]], code: str) -> Optional[Dict[str, Any]]:
    return next((l for l in lands if str(l.get("code")) == str(code)), None)

def find_by_index(lands: List[Dict[str, Any]], idx: int) -> Optional[Dict[str, Any]]:
    if 0 <= idx < len(lands):
        return lands[idx]
    return None

def expiry_meta(ad: Dict[str, Any]) -> Dict[str, Any]:
    """
    خروجی:
      status: 'unlimited' | 'today' | 'days'
      days_left: int | None
      label: متن آماده نمایش
    """
    exp_str = ad.get("expires_at")
    if not exp_str:
        return {"status": "unlimited", "days_left": None, "label": "نامحدود"}
    exp_dt = parse_iso_to_naive_utc(exp_str)
    if not exp_dt:
        return {"status": "unlimited", "days_left": None, "label": "نامحدود"}
    now = utcnow()
    days_left = (exp_dt.date() - now.date()).days
    if days_left <= 0:
        return {"status": "today", "days_left": 0, "label": "امروز منقضی می‌شود"}
    return {"status": "days", "days_left": days_left, "label": f"{days_left} روز مانده"}

# -----------------------------------------------------------------------------
# پاکسازی آگهی‌های منقضی (حذف کامل + حذف تصاویر)
# -----------------------------------------------------------------------------
def _safe_unlink(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def _delete_ad_images(ad: Dict[str, Any]):
    imgs = ad.get("images") or []
    if isinstance(imgs, str):
        imgs = [imgs]
    for img in imgs:
        if not isinstance(img, str) or not img:
            continue
        candidates = []
        if os.path.isabs(img):
            candidates.append(img)
        else:
            candidates.append(os.path.join(_uploads_root(), img))
            candidates.append(os.path.join(_uploads_root(), os.path.basename(img)))
        
            if img.startswith('static/'):
                candidates.append(os.path.join(current_app.root_path, img))
        for c in candidates:
            try:
                abs_c = os.path.abspath(c)
                uploads_root = os.path.abspath(_uploads_root())
                if abs_c.startswith(uploads_root) or ('/static/uploads/' in abs_c.replace('\\', '/')):
                    _safe_unlink(abs_c)
            except Exception:
                pass

def cleanup_expired_ads() -> None:
    """حذف کامل آگهی‌های منقضی‌شده از JSON و حذف تصاویرشان."""
    try:
        lands_path = _lands_path()
        lands = load_json(lands_path)
        if not isinstance(lands, list) or not lands:
            return

        kept: List[Dict[str, Any]] = []
        changed = False

        for ad in lands:
            exp_str = ad.get("expires_at")
            expired_flag = False
            if exp_str:
                exp_dt = parse_iso_to_naive_utc(exp_str)
                if exp_dt is None or exp_dt < utcnow():
                    expired_flag = True

            if expired_flag:
                try:
                    _delete_ad_images(ad)
                except Exception as e:
                    # لاگ خطا در صورت عدم موفقیت در حذف تصاویر
                    try:
                        current_app.logger.warning(f"Failed to delete images for expired ad {ad.get('code')}: {e}")
                    except Exception:
                        pass
                changed = True
                continue
            kept.append(ad)

        if changed:
            try:
                save_json(lands_path, kept)
                try:
                    current_app.logger.info(f"Cleaned up {len(lands) - len(kept)} expired ads")
                except Exception:
                    pass
            except Exception as e:
                # لاگ خطا در صورت عدم موفقیت در ذخیره
                try:
                    current_app.logger.error(f"Failed to save cleaned ads: {e}")
                except Exception:
                    pass
    except Exception as e:
        # لاگ خطای کلی
        try:
            current_app.logger.error(f"Error in cleanup_expired_ads: {e}")
        except Exception:
            pass

# -----------------------------------------------------------------------------
# دکوراتور لاگین
# -----------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin.login'))
        return view(*args, **kwargs)
    return wrapper

# -----------------------------------------------------------------------------
# احراز هویت
# -----------------------------------------------------------------------------

@admin_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    """
    نکته امنیتی:
    - در تمپلیت admin/login.html حتماً CSRF token بگذارید:
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    - تا قبل از اضافه شدن توکن در فرم، می‌توانید موقتاً این روت را CSRF-exempt کنید.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True  # ماندگاری session برای PWA
            flash('خوش آمدید؛ ورود موفق.', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    return render_template('admin/login.html')

# معافیت موقت CSRF فقط برای لاگین (پس از افزودن توکن، این را حذف کنید)
if csrf is not None:
    admin_bp.view_functions['login'] = csrf.exempt(admin_bp.view_functions['login'])

@admin_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    # پاک کردن کامل session برای خروج کامل از حساب
    session.clear()
    session.permanent = False
    flash('خروج انجام شد.', 'info')
    return redirect(url_for('admin.login'))

# -----------------------------------------------------------------------------
# PWA Routes
# -----------------------------------------------------------------------------
@admin_bp.route('/manifest.webmanifest')
def admin_manifest():
    """سرو manifest برای PWA ادمین"""
    from flask import send_from_directory, Response
    import os
    
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    manifest_path = os.path.join(static_dir, 'admin-manifest.webmanifest')
    
    if os.path.exists(manifest_path):
        return send_from_directory(static_dir, 'admin-manifest.webmanifest', mimetype='application/manifest+json')
    
    # Fallback
    fallback = {
        "id": "/admin",
        "name": "پنل مدیریت وینور",
        "short_name": "وینور ادمین",
        "description": "پنل مدیریت وینور اکسپرس",
        "dir": "rtl",
        "lang": "fa",
        "start_url": "/admin/?source=pwa",
        "scope": "/admin/",
        "display": "standalone",
        "background_color": "#7C3AED",
        "theme_color": "#7C3AED",
        "icons": [
            { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
            { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
        ]
    }
    return Response(json.dumps(fallback, ensure_ascii=False), mimetype='application/manifest+json')

@admin_bp.route('/sw.js')
def admin_service_worker():
    """سرو service worker برای PWA ادمین"""
    from flask import send_from_directory
    import os
    
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    sw_path = os.path.join(static_dir, 'admin-sw.js')
    
    if os.path.exists(sw_path):
        return send_from_directory(static_dir, 'admin-sw.js', mimetype='application/javascript')
    
    return ('// Admin Service Worker not found', 404)

# -----------------------------------------------------------------------------
# داشبورد و صفحات کلی
# -----------------------------------------------------------------------------
@admin_bp.route('/select', endpoint='select_portal')
@login_required
def select_portal():
    """صفحه انتخاب پنل بعد از لاگین: وینور اصلی یا وینور اکسپرس."""
    return render_template('admin/select_portal.html')

@admin_bp.route('', endpoint='admin_root', strict_slashes=False)
@admin_bp.route('/', endpoint='dashboard', strict_slashes=False)
@login_required
def dashboard():
    """داشبورد همکاران - فقط اطلاعات مربوط به همکاران"""
    try:
        partners = load_express_partners() or []
        applications = load_express_partner_apps() or []
        assignments = load_express_assignments() or []
        commissions = load_express_commissions() or []
    except Exception:
        partners = []
        applications = []
        assignments = []
        commissions = []
    
    # شمارش درخواست‌های در انتظار
    pending_apps = [a for a in applications if isinstance(a, dict) and a.get('status') not in ('approved', 'rejected')]
    
    return render_template(
        'admin/dashboard.html',
        partners_count=len(partners) if isinstance(partners, list) else 0,
        applications_count=len(pending_apps),
        assignments_count=len(assignments) if isinstance(assignments, list) else 0,
        commissions_count=len(commissions) if isinstance(commissions, list) else 0
    )

@admin_bp.route('/users')
@login_required
def users_page():
    try:
        users = load_users()
    except Exception:
        users = []

    # جستجو و مرتب‌سازی ساده
    q = (request.args.get('q') or '').strip().lower()
    sort = (request.args.get('sort') or 'created_desc').strip()

    safe_users = users if isinstance(users, list) else []
    if q:
        def _hit(u):
            phone = str(u.get('phone') or u.get('mobile') or '')
            email = str(u.get('email') or '')
            name  = str(u.get('name') or u.get('fullname') or '')
            return (q in phone.lower()) or (q in email.lower()) or (q in name.lower())
        safe_users = [u for u in safe_users if _hit(u)]

    def _int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    if sort == 'last_login_desc':
        safe_users.sort(key=lambda u: _int(u.get('last_login_ts') or u.get('last_login'), 0), reverse=True)
    elif sort == 'last_login_asc':
        safe_users.sort(key=lambda u: _int(u.get('last_login_ts') or u.get('last_login'), 0))
    elif sort == 'created_asc':
        safe_users.sort(key=lambda u: _int(u.get('created_at_ts') or u.get('created_at'), 0))
    else:  # created_desc
        safe_users.sort(key=lambda u: _int(u.get('created_at_ts') or u.get('created_at'), 0), reverse=True)

    # آمار
    total_users = len(users) if isinstance(users, list) else 0
    active_users = 0
    new_users_7d = 0
    verified_users = 0
    now_ts = int(datetime.utcnow().timestamp())
    for u in users if isinstance(users, list) else []:
        if u.get('is_active'):
            active_users += 1
        else:
            ts = _int(u.get('last_login_ts') or u.get('last_login'), 0)
            if ts and (now_ts - ts) <= 30*24*3600:
                active_users += 1
        cts = _int(u.get('created_at_ts') or u.get('created_at'), 0)
        if cts and (now_ts - cts) <= 7*24*3600:
            new_users_7d += 1
        if any(bool(u.get(k)) for k in ('is_verified','verified','phone_verified')):
            verified_users += 1

    # صفحه‌بندی ساده
    page = int(request.args.get('page', 1) or 1)
    per_page = min(int(request.args.get('per_page', 20) or 20), 100)
    total = len(safe_users)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    items = safe_users[start:start+per_page]

    return render_template(
        'admin/users.html',
        users=items,
        total_users=total_users,
        active_users=active_users,
        new_users_7d=new_users_7d,
        verified_users=verified_users,
        q=q,
        sort=sort,
        page=page,
        pages=pages,
    )

# -----------------------------------------------------------------------------
# ارسال اعلان همگانی به همهٔ کاربران
# -----------------------------------------------------------------------------
@admin_bp.route('/notifications/broadcast', methods=['GET', 'POST'])
@login_required
def notifications_broadcast():
    message = None
    error = None
    # Diagnostics for push configuration/subscribers
    try:
        subs_for_diag = _load_subs()
    except Exception:
        subs_for_diag = []
    push_diag = {
        'has_public': bool(current_app.config.get('VAPID_PUBLIC_KEY')),
        'has_private': bool(current_app.config.get('VAPID_PRIVATE_KEY')),
        'subs_count': len(subs_for_diag or []),
    }
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        body  = (request.form.get('body') or '').strip()
        ntype = (request.form.get('type') or 'info').strip() or 'info'
        # واکشی کاربران
        try:
            users = load_users()
        except Exception:
            users = []
        user_ids = []
        for u in users if isinstance(users, list) else []:
            uid = str(u.get('id') or u.get('user_id') or u.get('phone') or u.get('mobile') or '').strip()
            if uid:
                user_ids.append(uid)
        if not title or not body:
            error = 'عنوان و متن اعلان الزامی است.'
        elif not user_ids:
            error = 'هیچ کاربری یافت نشد.'
        else:
            sent = 0
            # ثبت اعلان در in-app notifications
            for uid in user_ids:
                try:
                    add_notification(uid, title=title, body=body, ntype=ntype)
                    sent += 1
                except Exception:
                    pass

            # تلاش برای ارسال Web Push با صدا (در کلاینت)
            try:
                subs = _load_subs()
            except Exception:
                subs = []
            push_sent = 0
            payload = {
                "title": title,
                "body": body,
                "icon": "/static/icons/icon-192.png",
                "badge": "/static/icons/monochrome-192.png",
                "url": url_for('main.app_home', _external=True),
                "sound": "/static/sounds/notify.mp3"
            }
            for s in subs:
                res = _send_one(s, payload)
                if res.get('ok'): push_sent += 1
            message = f'اعلان برای {sent} کاربر ثبت و {push_sent} پوش ارسال شد.'
            # update diagnostics after send
            try:
                subs_for_diag = _load_subs()
            except Exception:
                subs_for_diag = []
            push_diag.update({'subs_count': len(subs_for_diag or [])})

    return render_template('admin/broadcast.html', message=message, error=error, push_diag=push_diag)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        approval_method = request.form.get('approval_method', 'manual')

        # مقدار انتخابی از UI: 0 (نامحدود) یا 30/60/90
        raw_exp = request.form.get('ad_expiry_days', '30')
        try:
            ad_expiry_days = int(raw_exp)
        except Exception:
            ad_expiry_days = 30
        if ad_expiry_days < 0:
            ad_expiry_days = 0
        if ad_expiry_days not in (0, 30, 60, 90):
            ad_expiry_days = 30

        try:
            post_price_toman = int(request.form.get('ad_post_price_toman', '10000') or '10000')
        except Exception:
            post_price_toman = 10000
        if post_price_toman < 0:
            post_price_toman = 0

        save_settings({
            'approval_method': approval_method,
            'ad_expiry_days': ad_expiry_days,
            'show_submit_button': (request.form.get('show_submit_button') == 'on'),
            'ad_post_price_toman': post_price_toman,
        })
        flash('تنظیمات با موفقیت ذخیره شد.', 'success')
        return redirect(url_for('admin.settings'))

    cleanup_expired_ads()
    lands = load_json(_lands_path())
    p, a, r = counts_by_status(lands if isinstance(lands, list) else [])
    settings_data = get_settings()
    return render_template('admin/settings.html',
                           settings=settings_data,
                           pending_count=p, approved_count=a, rejected_count=r)

# -----------------------------------------------------------------------------
# فهرست آگهی‌ها (با صفحه‌بندی)
# -----------------------------------------------------------------------------
@admin_bp.route('/lands')
@login_required
def lands():
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    # متای نمایش اعتبار
    for ad in lands_list:
        ad["_expiry"] = expiry_meta(ad)

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", PER_PAGE_DEFAULT))
    pagination = paginate(lands_list, page, per_page)
    p, a, r = counts_by_status(lands_list)
    return render_template(
        'admin/lands.html',
        lands=pagination["items"],
        pagination={"page": pagination["page"], "pages": pagination["pages"]},
        pending_count=p, approved_count=a, rejected_count=r
    )

@admin_bp.route('/pending-lands')
@login_required
def pending_lands():
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    subset = [l for l in lands_list if str(l.get("status", "pending")) == "pending"]
    for ad in subset:
        ad["_expiry"] = expiry_meta(ad)

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", PER_PAGE_DEFAULT))
    pagination = paginate(subset, page, per_page)
    p, a, r = counts_by_status(lands_list)
    return render_template(
        'admin/pending_lands.html',
        lands=pagination["items"],
        pagination={"page": pagination["page"], "pages": pagination["pages"]},
        pending_count=p, approved_count=a, rejected_count=r
    )

@admin_bp.route('/approved-lands')
@login_required
def approved_lands():
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    subset = [l for l in lands_list if str(l.get("status")) == "approved"]
    for ad in subset:
        ad["_expiry"] = expiry_meta(ad)

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", PER_PAGE_DEFAULT))
    pagination = paginate(subset, page, per_page)
    p, a, r = counts_by_status(lands_list)
    return render_template(
        'admin/approved_lands.html',
        lands=pagination["items"],
        pagination={"page": pagination["page"], "pages": pagination["pages"]},
        pending_count=p, approved_count=a, rejected_count=r
    )

@admin_bp.route('/rejected-lands')
@login_required
def rejected_lands():
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    subset = [l for l in lands_list if str(l.get("status")) == "rejected"]
    for ad in subset:
        ad["_expiry"] = expiry_meta(ad)

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", PER_PAGE_DEFAULT))
    pagination = paginate(subset, page, per_page)
    p, a, r = counts_by_status(lands_list)
    return render_template(
        'admin/rejected_lands.html',
        lands=pagination["items"],
        pagination={"page": pagination["page"], "pages": pagination["pages"]},
        pending_count=p, approved_count=a, rejected_count=r
    )

# -----------------------------------------------------------------------------
# گزارش‌های کاربران (Reported Ads)
# -----------------------------------------------------------------------------
@admin_bp.route('/reports')
@login_required
def reports_list():
    items = load_reports() or []
    if not isinstance(items, list):
        items = []
    # تازه‌ترین بالا
    try:
        items.sort(key=lambda x: x.get('created_at',''), reverse=True)
    except Exception:
        pass
    page = int(request.args.get('page', 1) or 1)
    per_page = int(request.args.get('per_page', 20) or 20)
    pagination = paginate(items, page, per_page)
    return render_template(
        'admin/reports.html',
        reports=pagination['items'],
        pagination={"page": pagination["page"], "pages": pagination["pages"]}
    )

@admin_bp.post('/reports/<int:rid>/resolve')
@login_required
def report_resolve(rid: int):
    items = load_reports() or []
    if not isinstance(items, list):
        items = []
    changed = False
    for r in items:
        try:
            if int(r.get('id', 0)) == int(rid):
                r['status'] = 'resolved'
                r['resolved_at'] = iso_z(utcnow())
                changed = True
                break
        except Exception:
            continue
    if changed:
        save_reports(items)
    return redirect(url_for('admin.reports_list'))

# -----------------------------------------------------------------------------
# مشاهده آگهی
# -----------------------------------------------------------------------------
@admin_bp.route('/land/<string:code>')
@login_required
def view_land(code):
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    land = find_by_code(lands_list, code)
    if not land:
        abort(404)
    p, a, r = counts_by_status(lands_list)
    return render_template('admin/land_view.html', land=land,
                           pending_count=p, approved_count=a, rejected_count=r)

@admin_bp.route('/land/index/<int:land_id>')
@login_required
def view_land_by_index(land_id):
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    land = find_by_index(lands_list, land_id)
    if not land:
        abort(404)
    p, a, r = counts_by_status(lands_list)
    return render_template('admin/land_view.html', land=land,
                           pending_count=p, approved_count=a, rejected_count=r)

# -----------------------------------------------------------------------------
# ثبت/ویرایش/حذف آگهی (پشتیبانی همزمان از آپلود فایل و ورودی متنی تصاویر)
# -----------------------------------------------------------------------------
def _next_numeric_code(lands: List[Dict[str, Any]]) -> str:
    existing_codes = [
        int(l['code']) for l in lands
        if isinstance(l, dict) and 'code' in l and str(l['code']).isdigit()
    ]
    return str(max(existing_codes) + 1) if existing_codes else '1'

def _normalize_images_from_form(form, files) -> List[str]:
    """
    پذیرش هر دو ورودی:
    - images[] متنی (URL/مسیر)
    - images فایل
    ذخیره فایل‌ها در static/uploads و برگرداندن مسیر نسبی مثل 'uploads/filename.jpg'
    """
    image_urls: List[str] = []

    # متنی
    text_list = form.getlist('images') or []
    for t in text_list:
        t = (t or '').strip()
        if t:
            image_urls.append(t)

    # فایل
    upload_files = files.getlist('images')
    if upload_files:
        upload_folder = _uploads_root()
        os.makedirs(upload_folder, exist_ok=True)
        for f in upload_files:
            if f and f.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}__{f.filename}")
                f.save(os.path.join(upload_folder, filename))
                image_urls.append(f'uploads/{filename}')

    return image_urls

@admin_bp.route('/add-land', methods=['GET', 'POST'])
@login_required
def add_land():
    lands = load_json(_lands_path())
    if not isinstance(lands, list):
        lands = []

    if request.method == 'POST':
        form = request.form

        settings = get_settings()
        approval_method = settings.get('approval_method', 'manual')
        status = 'approved' if approval_method == 'auto' else 'pending'

        # محاسبه تاریخ‌ها (۰ = نامحدود → expires_at ست نمی‌شود)
        created_at_dt = utcnow()
        try:
            expiry_days = int(settings.get('ad_expiry_days', 30))
        except Exception:
            expiry_days = 30
        if expiry_days < 0:
            expiry_days = 0

        new_code = form.get("code") or _next_numeric_code(lands)
        images = _normalize_images_from_form(request.form, request.files)

        new_land = {
            'code': str(new_code),
            'title': form.get('title', '').strip() or 'بدون عنوان',
            'size': form.get('size', '').strip(),
            'location': form.get('location', '').strip(),
            'category': form.get('category', '').strip(),
            'document_type': form.get('document_type', '').strip(),
            'description': form.get('description', '').strip(),
            'features': form.getlist('features'),
            'price_total': form.get('price_total', '').strip(),
            'price_per_meter': form.get('price_per_meter', '').strip(),
            'images': images,
            'approval_method': approval_method,
            'status': status,
            'created_at': iso_z(created_at_dt),
            # اگر ادمین به اسم کاربر خاص ثبت می‌کند، می‌تواند owner را نیز ست کند:
            'owner': form.get('owner', '').strip() or None,
        }

        if expiry_days > 0:
            expires_at_dt = created_at_dt + timedelta(days=expiry_days)
            new_land['expires_at'] = iso_z(expires_at_dt)

        lands.append(new_land)
        save_json(_lands_path(), lands)

        # ✅ اعلان (در صورت داشتن owner)
        notify_admin_create(new_land)

        flash(f'آگهی با کد {new_code} با موفقیت ثبت شد.', 'success')
        return redirect(url_for('admin.lands'))

    # GET
    cleanup_expired_ads()
    p, a, r = counts_by_status(lands if isinstance(lands, list) else [])
    return render_template('admin/add_land.html',
                           pending_count=p, approved_count=a, rejected_count=r)

# ویرایش – سازگاری با هر دو الگو: querystring code/land_id و مسیر <int:land_id>
@admin_bp.route('/edit-land', methods=['GET', 'POST'])
@admin_bp.route('/edit-land/<int:land_id>', methods=['GET', 'POST'])
@login_required
def edit_land(land_id: Optional[int] = None):
    cleanup_expired_ads()
    lands = load_json(_lands_path())
    if not isinstance(lands, list):
        lands = []

    code = request.args.get("code") or request.form.get("code")
    land = None

    if code:
        land = find_by_code(lands, code)
        land_index = lands.index(land) if land in lands else None
    elif land_id is not None:
        land = find_by_index(lands, land_id)
        land_index = land_id
    else:
        land_index = None

    if not land or land_index is None:
        flash('آگهی مورد نظر پیدا نشد.', 'warning')
        return redirect(url_for('admin.lands'))

    if request.method == 'POST':
        form = request.form
        # فیلدها
        land.update({
            'title': form.get('title', '').strip() or land.get('title', ''),
            'size': form.get('size', '').strip() or land.get('size', ''),
            'location': form.get('location', '').strip() or land.get('location', ''),
            'code': str(form.get('code', land.get('code', ''))).strip() or land.get('code', ''),
            'category': form.get('category', '').strip() or land.get('category', ''),
            'document_type': form.get('document_type', '').strip() or land.get('document_type', ''),
            'description': form.get('description', '').strip() or land.get('description', ''),
            'features': form.getlist('features') or land.get('features', []),
            'price_total': form.get('price_total', '').strip() or land.get('price_total', ''),
            'price_per_meter': form.get('price_per_meter', '').strip() or land.get('price_per_meter', ''),
            'status': form.get('status', land.get('status', 'pending'))
        })

        # حذف همه تصاویر (اختیاری)
        if request.form.get('remove_all_images') == 'on':
            for img in land.get('images', []):
                path = os.path.join(current_app.static_folder, img)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            land['images'] = []

        # افزودن تصاویر جدید (متنی/فایل)
        new_images = _normalize_images_from_form(request.form, request.files)
        if new_images:
            land.setdefault('images', []).extend(new_images)

        save_json(_lands_path(), lands)

        # ✅ اعلان: ویرایش توسط ادمین
        notify_admin_edit(land)

        flash('آگهی ویرایش شد.', 'success')
        return redirect(url_for('admin.lands'))

    p, a, r = counts_by_status(lands)
    return render_template('admin/edit_land.html', land=land, land_id=land_index,
                           pending_count=p, approved_count=a, rejected_count=r)

# حذف – سازگاری با هر دو الگو: querystring/route
@admin_bp.route('/delete-land', methods=['POST'])
@admin_bp.route('/delete-land/<int:land_id>', methods=['POST'])
@login_required
def delete_land(land_id: Optional[int] = None):
    lands = load_json(_lands_path())
    if not isinstance(lands, list):
        lands = []

    code = request.args.get("code") or request.form.get("code")
    idx_to_delete = None

    if code:
        for i, l in enumerate(lands):
            if str(l.get("code")) == str(code):
                idx_to_delete = i
                break
    elif land_id is not None:
        if 0 <= land_id < len(lands):
            idx_to_delete = land_id

    if idx_to_delete is None:
        abort(404)

    land = lands.pop(idx_to_delete)
    # حذف فایل‌های تصویر روی دیسک
    _delete_ad_images(land)

    # استفاده از save_ads برای همگام‌سازی کش سمت کاربر
    save_ads(lands)
    flash('آگهی با موفقیت حذف شد.', 'success')
    return redirect(url_for('admin.lands'))

# -----------------------------------------------------------------------------
# تغییر وضعیت: تأیید/رد
# -----------------------------------------------------------------------------
@admin_bp.route('/approve/<string:code>', methods=['POST'])
@admin_bp.route('/approve-land/<string:code>', methods=['POST'])
@login_required
def approve_land(code):
    cleanup_expired_ads()
    lands = load_json(_lands_path())
    land = find_by_code(lands if isinstance(lands, list) else [], code)
    if not land:
        flash('آگهی یافت نشد.', 'warning')
        return redirect(request.referrer or url_for('admin.pending_lands'))
    land['status'] = 'approved'
    try:
        land['approved_at'] = iso_z(utcnow())
    except Exception:
        pass
    save_ads(lands)

    # ✅ اعلان: تأیید شد
    notify_status_change(land, 'approved')

    flash('آگهی تأیید شد.', 'success')
    return redirect(request.referrer or url_for('admin.approved_lands'))

@admin_bp.route('/reject/<string:code>', methods=['POST'])
@admin_bp.route('/reject-land/<string:code>', methods=['POST'])
@login_required
def reject_land(code):
    cleanup_expired_ads()
    lands = load_json(_lands_path())
    land = find_by_code(lands if isinstance(lands, list) else [], code)
    if not land:
        flash('آگهی یافت نشد.', 'warning')
        return redirect(request.referrer or url_for('admin.pending_lands'))

    land['status'] = 'rejected'
    reason = request.form.get("reject_reason", "").strip()
    if reason:
        land["reject_reason"] = reason

    save_ads(lands)

    # ✅ اعلان: رد شد + دلیل
    notify_status_change(land, 'rejected', reason=reason or None)

    flash('آگهی رد شد / نیاز به اصلاح دارد.', 'info')
    return redirect(request.referrer or url_for('admin.rejected_lands'))

# -----------------------------------------------------------------------------
# Express Listings Management
# -----------------------------------------------------------------------------
@admin_bp.route('/express')
@login_required
def express_listings():
    """لیست آگهی‌های اکسپرس"""
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    
    # فیلتر آگهی‌های اکسپرس
    express_lands = [land for land in lands_list if land.get('is_express', False)]
    
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", PER_PAGE_DEFAULT))
    pagination = paginate(express_lands, page, per_page)
    
    p, a, r = counts_by_status(express_lands)
    return render_template(
        'admin/express_listings.html',
        lands=pagination["items"],
        pagination={"page": pagination["page"], "pages": pagination["pages"]},
        pending_count=p, approved_count=a, rejected_count=r
    )


@admin_bp.post('/express/transfer')
@login_required
def express_transfer():
    """انتقال داده‌های اکسپرس از مجموعه داده‌های وینور به ساختار اکسپرس (idempotent)."""
    # داده‌ها در فایل‌های JSON ذخیره می‌شوند؛ این تابع اقلام مرتبط را به فایل‌های مقصد merge می‌کند
    try:
        # مبداً: lands.json حاوی آگهی‌هایی که ممکن است فیلدهای express داشته باشند
        lands = load_json(_lands_path()) or []
        if not isinstance(lands, list):
            lands = []

        # مقصدها: فایل‌های express_*
        partners = load_express_partners() or []
        partner_apps = load_express_partner_apps() or []
        assignments = load_express_assignments() or []
        commissions = load_express_commissions() or []

        # از app.routes.public توابع کمکی بارگذاری متعلقات همکار استفاده نمی‌کنیم؛ تنها merge ایمن
        # چون در این پروژه، متعلقات همکار در فایل‌های جدا ذخیره می‌شوند، انتقال اینجا idempotent است.

        # اگر آگهی‌های اکسپرس در lands باشند، فقط ensure کنیم is_express و express_status ست است.
        changed_lands = False
        for ad in lands:
            if ad.get('is_express') and not ad.get('ad_type'):
                ad['ad_type'] = 'express'
                changed_lands = True
            if ad.get('is_express') and not ad.get('express_status'):
                ad['express_status'] = str(ad.get('status') or 'approved')
                changed_lands = True
        if changed_lands:
            save_ads(lands)

        # چون داده‌های partner_* در فایل‌های مستقل هستند، تنها normalize ساده انجام می‌دهیم
        def _unique(items, key):
            seen = set()
            out = []
            for it in items:
                k = str(it.get(key))
                if not k or k in seen:
                    continue
                seen.add(k)
                out.append(it)
            return out

        save_express_partners(partners if isinstance(partners, list) else [])
        save_express_partner_apps(partner_apps if isinstance(partner_apps, list) else [])
        save_express_assignments(assignments if isinstance(assignments, list) else [])
        save_express_commissions(commissions if isinstance(commissions, list) else [])

        flash('انتقال داده‌های اکسپرس انجام شد.', 'success')
    except Exception as e:
        current_app.logger.error(f"Express transfer error: {e}")
        flash('خطا در اجرای انتقال.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/express/add', methods=['GET', 'POST'])
@login_required
def add_express_listing():
    """افزودن آگهی اکسپرس جدید"""
    if request.method == 'POST':
        form = request.form
        files = request.files
        
        # اعتبارسنجی فیلدهای اجباری
        title = form.get('title', '').strip()
        location = form.get('location', '').strip()
        size_raw = form.get('size', '').strip()
        price_total_raw = form.get('price_total', '').strip()
        
        # پاک کردن فرمت از اعداد (حذف کاما و کاراکترهای غیر عددی)
        size_clean = re.sub(r'[^\d]', '', size_raw) if size_raw else ''
        price_total_clean = re.sub(r'[^\d]', '', price_total_raw) if price_total_raw else ''
        
        if not all([title, location, size_clean, price_total_clean]):
            flash('لطفاً فیلدهای اجباری را پر کنید.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        
        if len(title) < 10:
            flash('عنوان باید حداقل ۱۰ کاراکتر باشد.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        
        # تبدیل به عدد
        try:
            size = int(size_clean)
            price_total = int(price_total_clean)
        except (ValueError, TypeError):
            flash('متراژ و قیمت باید عدد معتبر باشند.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        
        if size <= 0 or price_total <= 0:
            flash('متراژ و قیمت باید بیشتر از صفر باشند.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        
        # بارگذاری لیست آگهی‌ها برای تولید کد
        lands = load_json(_lands_path())
        if not isinstance(lands, list):
            lands = []
        
        # تولید کد منحصر به فرد
        new_code = form.get("code") or _next_numeric_code(lands)
        
        # ذخیره مدارک
        documents = []
        for key, file in files.items():
            if key.startswith('document_') and file.filename:
                doc_filename = _save_express_document(file, new_code)
                if doc_filename:
                    documents.append(doc_filename)
        
        # پردازش تصاویر (از input multiple)
        images = []
        if 'images' in files:
            upload_folder = _uploads_root()
            os.makedirs(upload_folder, exist_ok=True)
            for file in files.getlist('images'):
                if file.filename:
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}__{file.filename}")
                    file.save(os.path.join(upload_folder, filename))
                    images.append(f'uploads/{filename}')
        
        # کمیسیون همکاران (الزامی)
        pct_raw = (form.get('express_commission_pct') or '').strip()
        if not pct_raw:
            flash('درصد پورسانت الزامی است.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        try:
            express_commission_pct = float(pct_raw)
            if express_commission_pct <= 0 or express_commission_pct > 100:
                flash('درصد پورسانت باید بین ۰ و ۱۰۰ باشد.', 'error')
                return render_template('admin/add_express_listing.html',
                                      pending_count=0, approved_count=0, rejected_count=0)
        except (ValueError, TypeError):
            flash('درصد پورسانت باید یک عدد معتبر باشد.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        # محاسبه قیمت در متر
        price_per_meter_raw = form.get('price_per_meter', '').strip()
        price_per_meter_clean = re.sub(r'[^\d]', '', price_per_meter_raw) if price_per_meter_raw else ''
        try:
            price_per_meter = int(price_per_meter_clean) if price_per_meter_clean else 0
            # اگر قیمت در متر محاسبه نشده، خودمان محاسبه می‌کنیم
            if price_per_meter == 0 and size > 0:
                price_per_meter = int(round(price_total / size))
        except (ValueError, TypeError):
            price_per_meter = int(round(price_total / size)) if size > 0 else 0
        
        # محاسبه کمیسیون
        try:
            price_int = price_total  # قبلاً تبدیل شده
        except Exception:
            price_int = 0
        express_commission_amount = int(round(price_int * ((express_commission_pct or 0)/100.0))) if price_int and (express_commission_pct is not None) else None

        # دریافت مختصات جغرافیایی
        latitude = None
        longitude = None
        try:
            lat_str = form.get('latitude', '').strip()
            lon_str = form.get('longitude', '').strip()
            if lat_str:
                latitude = float(lat_str)
            if lon_str:
                longitude = float(lon_str)
        except (ValueError, TypeError):
            pass  # اگر مقدار نامعتبر بود، None می‌ماند

        # ایجاد آگهی اکسپرس
        new_express_land = {
            'code': new_code,
            'title': title,
            'location': location,
            'size': size,  # حالا int است
            'price_total': price_total,  # حالا int است
            'price_per_meter': price_per_meter,
            'description': form.get('description', '').strip(),
            'images': images,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'owner': 'vinor_support',  # شماره پشتیبانی وینور
            'status': 'approved',  # آگهی‌های اکسپرس مستقیماً تأیید می‌شوند
            'ad_type': 'express',
            'category': form.get('category', ''),
            'is_express': True,
            'express_status': 'approved',
            'express_documents': documents,
            'vinor_contact': form.get('vinor_contact', '09121234567'),
            'extras': {
                'express_commission_pct': express_commission_pct,
                'express_commission_amount': express_commission_amount,
            }
        }
        
        # افزودن مختصات جغرافیایی در صورت وجود
        if latitude is not None:
            new_express_land['latitude'] = latitude
        if longitude is not None:
            new_express_land['longitude'] = longitude
        
        # ذخیره در فایل
        lands = load_json(_lands_path())
        lands.append(new_express_land)
        save_ads(lands)
        
        # ارسال نوتیفیکیشن به کاربران منطقه
        # در صورت انتخاب «ارسال خودکار برای تمامی همکاران» → ساخت انتساب برای همه + اعلان
        if (form.get('auto_send_all_partners') or '').strip():
            try:
                partners = load_express_partners() or []
                items = load_express_assignments() or []
                existing = {(str(a.get('partner_phone')), str(a.get('land_code'))) for a in items if isinstance(a, dict)}
                for p in partners:
                    phone = str((p or {}).get('phone') or '').strip()
                    if not phone:
                        continue
                    key = (phone, new_code)
                    if key not in existing:
                        new_id = (max([int(x.get('id',0) or 0) for x in items if isinstance(x, dict)], default=0) or 0) + 1
                        items.append({
                            'id': new_id,
                            'partner_phone': phone,
                            'land_code': new_code,
                            'commission_pct': express_commission_pct or 0,
                            'status': 'active',
                            'created_at': iso_z(utcnow())
                        })
                        existing.add(key)
                    try:
                        add_notification(
                            user_id=phone,
                            title='فایل جدید اکسپرس',
                            body=f"کد فایل: {new_code} - {title}",
                            ntype='info',
                            ad_id=new_code,
                            action_url=url_for('main.land_detail', code=new_code)
                        )
                    except Exception:
                        continue
                save_express_assignments(items)
            except Exception:
                pass
        
        flash(f'آگهی اکسپرس با کد {new_code} با موفقیت ثبت شد.', 'success')
        return redirect(url_for('admin.express_listings'))
    
    # GET
    cleanup_expired_ads()
    lands = load_json(_lands_path())
    p, a, r = counts_by_status(lands if isinstance(lands, list) else [])
    return render_template('admin/add_express_listing.html',
                          pending_count=p, approved_count=a, rejected_count=r)

@admin_bp.route('/express/<string:code>/edit', methods=['GET', 'POST'])
@login_required
def edit_express_listing(code):
    """ویرایش آگهی اکسپرس"""
    cleanup_expired_ads()
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    
    land = find_by_code(lands_list, code)
    if not land or not land.get('is_express', False):
        flash('آگهی اکسپرس یافت نشد.', 'warning')
        return redirect(url_for('admin.express_listings'))
    
    if request.method == 'POST':
        form = request.form
        files = request.files
        
        # به‌روزرسانی فیلدها
        land['title'] = form.get('title', '').strip()
        land['location'] = form.get('location', '').strip()
        land['size'] = form.get('size', '').strip()
        land['price_total'] = int(form.get('price_total', 0) or 0)
        land['price_per_meter'] = int(form.get('price_per_meter', 0) or 0)
        land['description'] = form.get('description', '').strip()
        land['vinor_contact'] = form.get('vinor_contact', '09121234567')
        
        # به‌روزرسانی مختصات جغرافیایی
        try:
            lat_str = form.get('latitude', '').strip()
            lon_str = form.get('longitude', '').strip()
            if lat_str:
                land['latitude'] = float(lat_str)
            else:
                land.pop('latitude', None)
            if lon_str:
                land['longitude'] = float(lon_str)
            else:
                land.pop('longitude', None)
        except (ValueError, TypeError):
            pass  # اگر مقدار نامعتبر بود، تغییر نمی‌دهیم
        
        # اضافه کردن تصاویر جدید
        for i in range(1, 4):  # image_1, image_2, image_3
            img_key = f'image_{i}'
            if img_key in files and files[img_key].filename:
                file = files[img_key]
                upload_folder = _uploads_root()
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}__{file.filename}")
                file.save(os.path.join(upload_folder, filename))
                land.setdefault('images', []).append(f'uploads/{filename}')
        
        # اضافه کردن مدارک جدید
        for key, file in files.items():
            if key.startswith('document_') and file.filename:
                doc_filename = _save_express_document(file, code)
                if doc_filename:
                    land.setdefault('express_documents', []).append(doc_filename)
        
        # ذخیره تغییرات
        save_json(_lands_path(), lands_list)
        flash('آگهی اکسپرس با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('admin.express_listings'))
    
    # GET
    p, a, r = counts_by_status(lands_list)
    return render_template('admin/edit_express_listing.html',
                          land=land,
                          pending_count=p, approved_count=a, rejected_count=r)

@admin_bp.post('/express/<string:code>/delete')
@login_required
def delete_express_listing(code):
    """حذف آگهی اکسپرس"""
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    
    land = find_by_code(lands_list, code)
    if not land or not land.get('is_express', False):
        flash('آگهی اکسپرس یافت نشد.', 'warning')
        return redirect(url_for('admin.express_listings'))
    
    # حذف تصاویر آگهی
    _delete_ad_images(land)
    
    # حذف از لیست
    lands_list = [l for l in lands_list if str(l.get('code')) != str(code)]
    save_ads(lands_list)
    save_ads(lands_list)
    
    flash(f'آگهی اکسپرس با کد {code} با موفقیت حذف شد.', 'success')
    return redirect(url_for('admin.express_listings'))

@admin_bp.post('/express/<string:code>/toggle-sold')
@login_required
def toggle_express_sold(code):
    """تغییر وضعیت فروخته شد / در انتظار فروش"""
    lands_data = load_json(_lands_path())
    lands_list = lands_data if isinstance(lands_data, list) else []
    
    land = find_by_code(lands_list, code)
    if not land or not land.get('is_express', False):
        flash('آگهی اکسپرس یافت نشد.', 'warning')
        return redirect(url_for('admin.express_listings'))
    
    current_status = land.get('express_status', 'active')
    if current_status == 'sold':
        land['express_status'] = 'active'
        # برگرداندن وضعیت انتساب‌ها به active
        assignments = load_express_assignments() or []
        for a in assignments:
            if str(a.get('land_code')) == str(code):
                a['status'] = 'active'
                a['transaction_holder'] = None
                a['transaction_started_at'] = None
        save_express_assignments(assignments)
        flash(f'آگهی {code} به حالت در انتظار فروش برگشت.', 'success')
    else:
        land['express_status'] = 'sold'
        flash(f'آگهی {code} به فروخته شد تغییر کرد.', 'success')
    
    save_ads(lands_list)
    return redirect(url_for('admin.express_listings'))

@admin_bp.route('/express-docs/<filename>')
@login_required
def serve_express_document(filename):
    """سرو کردن مدارک اکسپرس"""
    try:
        docs_dir = _get_express_docs_dir()
        return send_from_directory(docs_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving express document {filename}: {e}")
        abort(404)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Express Partners: Applications & Partners list + actions
# -----------------------------------------------------------------------------
@admin_bp.route('/express/partners/applications')
@login_required
def express_partner_applications():
    try:
        items = load_express_partner_apps() or []
        if not isinstance(items, list):
            items = []
        try:
            items.sort(key=lambda x: x.get('created_at',''), reverse=True)
        except Exception:
            pass
    except Exception:
        items = []
    return render_template('admin/express_partner_applications.html', items=items)

@admin_bp.route('/express/partners')
@login_required
def express_partners():
    try:
        partners = load_express_partners() or []
        if not isinstance(partners, list):
            partners = []
    except Exception:
        partners = []
    
    try:
        applications = load_express_partner_apps() or []
        if not isinstance(applications, list):
            applications = []
    except Exception:
        applications = []
    
    return render_template('admin/express_partners.html', partners=partners, applications=applications)


@admin_bp.post('/express/partners/<string:phone>/delete')
@login_required
def express_partner_delete(phone: str):
    phone = (phone or '').strip()
    if not phone:
        flash('شماره همراه معتبر نیست.', 'warning')
        return redirect(url_for('admin.express_partners'))
    try:
        partners = load_express_partners() or []
        filtered = [p for p in partners if str(p.get('phone') or '').strip() != phone]
        if len(filtered) == len(partners):
            flash('همکار یافت نشد.', 'warning')
            return redirect(url_for('admin.express_partners'))
        save_express_partners(filtered)
        flash('همکار با موفقیت حذف شد.', 'success')
    except Exception as e:
        current_app.logger.error(f"Failed to delete partner {phone}: {e}")
        flash('خطا در حذف همکار.', 'danger')
    return redirect(url_for('admin.express_partners'))


@admin_bp.post('/express/applications/<int:aid>/delete')
@login_required
def express_partner_application_delete(aid: int):
    try:
        apps = load_express_partner_apps() or []
        filtered = [app for app in apps if int(app.get('id', 0) or 0) != int(aid)]
        if len(filtered) == len(apps):
            flash('درخواست یافت نشد.', 'warning')
            return redirect(url_for('admin.express_partner_applications'))
        save_express_partner_apps(filtered)
        flash('درخواست حذف شد.', 'success')
    except Exception as e:
        current_app.logger.error(f"Failed to delete application {aid}: {e}")
        flash('حذف درخواست با خطا مواجه شد.', 'danger')
    return redirect(url_for('admin.express_partner_applications'))

# -----------------------------------------------------------------------------
# Express Assignments (assign lands to partners)
# -----------------------------------------------------------------------------
@admin_bp.route('/express/assignments')
@login_required
def express_assignments():
    try:
        items = load_express_assignments() or []
        if not isinstance(items, list):
            items = []
        items.sort(key=lambda x: x.get('created_at',''), reverse=True)
    except Exception:
        items = []
    # partners list for quick assignment - همه همکاران
    partners = load_express_partners() or []
    # lands pool - همه فایل‌های اکسپرس (بدون فیلتر وضعیت)
    lands = load_json(_lands_path()) or []
    express_pool = [l for l in lands if l.get('is_express', False)]
    return render_template('admin/express_assignments.html', items=items, partners=partners, lands=express_pool)

@admin_bp.post('/express/assignments/new')
@login_required
def express_assignment_new():
    partner_phone = (request.form.get('partner_phone') or '').strip()
    land_code = (request.form.get('land_code') or '').strip()
    commission_pct = (request.form.get('commission_pct') or '').strip()
    try:
        pct = float(commission_pct or '0')
    except Exception:
        pct = 0.0
    
    items = load_express_assignments() or []
    
    # اگر "همه همکاران" انتخاب شده
    if partner_phone == '__ALL__':
        partners = load_express_partners() or []
        count = 0
        for p in partners:
            phone = str(p.get('phone', '')).strip()
            if not phone:
                continue
            # چک کن که قبلاً این فایل به این همکار انتساب نشده باشد
            exists = any(a.get('partner_phone') == phone and a.get('land_code') == land_code for a in items)
            if not exists:
                new_id = (max([int(x.get('id',0) or 0) for x in items if isinstance(x, dict)], default=0) or 0) + 1
                items.append({
                    'id': new_id,
                    'partner_phone': phone,
                    'land_code': land_code,
                    'commission_pct': pct,
                    'status': 'active',
                    'created_at': iso_z(utcnow())
                })
                count += 1
        save_express_assignments(items)
        flash(f'فایل به {count} همکار اختصاص یافت.', 'success')
    else:
        new_id = (max([int(x.get('id',0) or 0) for x in items if isinstance(x, dict)], default=0) or 0) + 1
        items.append({
            'id': new_id,
            'partner_phone': partner_phone,
            'land_code': land_code,
            'commission_pct': pct,
            'status': 'active',
            'created_at': iso_z(utcnow())
        })
        save_express_assignments(items)
        flash('فایل به همکار اختصاص یافت.', 'success')
    
    return redirect(url_for('admin.express_assignments'))

@admin_bp.post('/express/assignments/<int:aid>/close')
@login_required
def express_assignment_close(aid: int):
    items = load_express_assignments() or []
    changed = False
    for a in items:
        try:
            if int(a.get('id',0) or 0) == int(aid):
                a['status'] = 'closed'
                a['closed_at'] = iso_z(utcnow())
                changed = True
                break
        except Exception:
            continue
    if changed:
        save_express_assignments(items)
        flash('انتساب بسته شد.', 'info')
    return redirect(url_for('admin.express_assignments'))

@admin_bp.post('/express/assignments/clear-all')
@login_required
def express_assignments_clear_all():
    save_express_assignments([])
    flash('همه انتساب‌ها پاک شدند.', 'info')
    return redirect(url_for('admin.express_assignments'))

# -----------------------------------------------------------------------------
# Express Commissions (list/approve/pay)
# -----------------------------------------------------------------------------
@admin_bp.route('/express/commissions')
@login_required
def express_commissions():
    try:
        items = load_express_commissions() or []
        if not isinstance(items, list):
            items = []
        items.sort(key=lambda x: x.get('created_at',''), reverse=True)
    except Exception:
        items = []
    return render_template('admin/express_commissions.html', items=items)

@admin_bp.post('/express/commissions/new')
@login_required
def express_commission_new():
    partner_phone = (request.form.get('partner_phone') or '').strip()
    land_code = (request.form.get('land_code') or '').strip()
    sale_amount = (request.form.get('sale_amount') or '').strip()
    commission_pct = (request.form.get('commission_pct') or '').strip()
    try:
        sale = int(str(sale_amount).replace(',','').strip() or '0')
    except Exception:
        sale = 0
    try:
        pct = float(commission_pct or '0')
    except Exception:
        pct = 0.0
    commission_amount = int(round(sale * (pct/100.0))) if sale and pct else 0
    items = load_express_commissions() or []
    new_id = (max([int(x.get('id',0) or 0) for x in items if isinstance(x, dict)], default=0) or 0) + 1
    items.append({
        'id': new_id,
        'partner_phone': partner_phone,
        'land_code': land_code,
        'sale_amount': sale,
        'commission_pct': pct,
        'commission_amount': commission_amount,
        'status': 'pending',
        'created_at': iso_z(utcnow())
    })
    save_express_commissions(items)
    flash('پورسانت ثبت شد (در انتظار تایید).', 'success')
    return redirect(url_for('admin.express_commissions'))

@admin_bp.post('/express/commissions/<int:cid>/approve')
@login_required
def express_commission_approve(cid: int):
    items = load_express_commissions() or []
    changed = False
    commission_record = None
    for c in items:
        try:
            if int(c.get('id',0) or 0) == int(cid):
                # فقط اگر در وضعیت pending باشد، تایید کن
                if c.get('status') == 'pending':
                    c['status'] = 'approved'
                    c['approved_at'] = iso_z(utcnow())
                    commission_record = c
                    changed = True
                break
        except Exception:
            continue
    if changed and commission_record:
        save_express_commissions(items)
        
        # تغییر وضعیت فایل به "فروخته شده" در انتساب‌ها
        try:
            land_code = str(commission_record.get('land_code', ''))
            if land_code:
                assignments = load_express_assignments() or []
                for a in assignments:
                    if str(a.get('land_code')) == land_code:
                        a['status'] = 'sold'
                        a['sold_at'] = iso_z(utcnow())
                        a.pop('transaction_holder', None)
                        a.pop('transaction_started_at', None)
                save_express_assignments(assignments)
        except Exception as e:
            current_app.logger.error(f"Error updating assignment status to sold: {e}")
        
        # به‌روزرسانی آمار همکار
        try:
            partner_phone = str(commission_record.get('partner_phone', '')).strip()
            commission_amount = int(commission_record.get('commission_amount') or 0)
            sale_amount = int(commission_record.get('sale_amount') or 0)
            
            if partner_phone:
                partners = load_express_partners() or []
                for p in partners:
                    if str(p.get('phone')) == partner_phone:
                        # افزودن به کل درآمد
                        current_income = int(p.get('total_income', 0) or 0)
                        p['total_income'] = current_income + commission_amount
                        
                        # افزودن به تعداد فروش‌های تایید شده
                        current_sales = int(p.get('approved_sales_count', 0) or 0)
                        p['approved_sales_count'] = current_sales + 1
                        
                        # افزودن به کل فروش‌های تایید شده
                        current_total_sales = int(p.get('total_approved_sales', 0) or 0)
                        p['total_approved_sales'] = current_total_sales + sale_amount
                        
                        p['last_updated'] = iso_z(utcnow())
                        break
                
                save_express_partners(partners)
        except Exception as e:
            current_app.logger.error(f"Error updating partner stats: {e}")
        
        flash('پورسانت تایید شد، فایل به فروخته شده تغییر کرد و آمار همکار به‌روز شد.', 'success')
    elif not changed:
        flash('پورسانت قبلاً تایید شده است.', 'warning')
    return redirect(url_for('admin.express_commissions'))

@admin_bp.post('/express/commissions/<int:cid>/pay')
@login_required
def express_commission_pay(cid: int):
    items = load_express_commissions() or []
    changed = False
    for c in items:
        try:
            if int(c.get('id',0) or 0) == int(cid):
                if c.get('status') == 'approved':
                    c['status'] = 'paid'
                    c['paid_at'] = iso_z(utcnow())
                    changed = True
                break
        except Exception:
            continue
    if changed:
        save_express_commissions(items)
        flash('پورسانت پرداخت شد.', 'success')
    elif not changed:
        flash('پورسانت باید ابتدا تایید شود.', 'warning')
    return redirect(url_for('admin.express_commissions'))

@admin_bp.post('/express/commissions/<int:cid>/reject')
@login_required
def express_commission_reject(cid: int):
    items = load_express_commissions() or []
    changed = False
    commission_record = None
    old_status = None
    for c in items:
        try:
            if int(c.get('id',0) or 0) == int(cid):
                old_status = c.get('status')
                if c.get('status') in ('pending', 'approved'):
                    c['status'] = 'rejected'
                    c['rejected_at'] = iso_z(utcnow())
                    commission_record = c
                    changed = True
                break
        except Exception:
            continue
    if changed and commission_record:
        save_express_commissions(items)
        
        # اگر قبلاً تایید شده بود و به آمار اضافه شده بود، از آمار کم کن
        if old_status == 'approved':
            try:
                partner_phone = str(commission_record.get('partner_phone', '')).strip()
                commission_amount = int(commission_record.get('commission_amount') or 0)
                sale_amount = int(commission_record.get('sale_amount') or 0)
                
                if partner_phone:
                    partners = load_express_partners() or []
                    for p in partners:
                        if str(p.get('phone')) == partner_phone:
                            # کم کردن از کل درآمد
                            current_income = int(p.get('total_income', 0) or 0)
                            p['total_income'] = max(0, current_income - commission_amount)
                            
                            # کم کردن از تعداد فروش‌های تایید شده
                            current_sales = int(p.get('approved_sales_count', 0) or 0)
                            p['approved_sales_count'] = max(0, current_sales - 1)
                            
                            # کم کردن از کل فروش‌های تایید شده
                            current_total_sales = int(p.get('total_approved_sales', 0) or 0)
                            p['total_approved_sales'] = max(0, current_total_sales - sale_amount)
                            
                            p['last_updated'] = iso_z(utcnow())
                            break
                    
                    save_express_partners(partners)
            except Exception as e:
                current_app.logger.error(f"Error updating partner stats after reject: {e}")
        
        flash('پورسانت رد شد.', 'info')
    elif not changed:
        flash('فقط پورسانت‌های در انتظار یا تایید شده قابل رد هستند.', 'warning')
    return redirect(url_for('admin.express_commissions'))

@admin_bp.post('/express/commissions/clear-all')
@login_required
def clear_all_commissions():
    save_express_commissions([])
    flash('همه پورسانت‌ها حذف شدند.', 'info')
    return redirect(url_for('admin.express_commissions'))

@admin_bp.route('/express/commissions/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def express_commission_edit(cid: int):
    items = load_express_commissions() or []
    commission = None
    for c in items:
        try:
            if int(c.get('id',0) or 0) == int(cid):
                commission = c
                break
        except Exception:
            continue
    
    if not commission:
        flash('پورسانت یافت نشد.', 'error')
        return redirect(url_for('admin.express_commissions'))
    
    if request.method == 'POST':
        form = request.form
        sale_amount = (form.get('sale_amount') or '').strip()
        commission_pct = (form.get('commission_pct') or '').strip()
        
        try:
            sale = int(str(sale_amount).replace(',','').strip() or '0')
        except Exception:
            sale = int(commission.get('sale_amount') or 0)
        
        try:
            pct = float(commission_pct or '0')
        except Exception:
            pct = float(commission.get('commission_pct') or 0)
        
        commission_amount = int(round(sale * (pct/100.0))) if sale and pct else 0
        
        # اگر پورسانت تایید شده است، باید آمار را به‌روز کنم
        old_sale = int(commission.get('sale_amount') or 0)
        old_commission = int(commission.get('commission_amount') or 0)
        is_approved = commission.get('status') == 'approved'
        
        # به‌روزرسانی رکورد
        commission['sale_amount'] = sale
        commission['commission_pct'] = pct
        commission['commission_amount'] = commission_amount
        commission['updated_at'] = iso_z(utcnow())
        
        save_express_commissions(items)
        
        # اگر تایید شده بود، آمار را به‌روز کن
        if is_approved and (sale != old_sale or commission_amount != old_commission):
            try:
                partner_phone = str(commission.get('partner_phone', '')).strip()
                if partner_phone:
                    partners = load_express_partners() or []
                    for p in partners:
                        if str(p.get('phone')) == partner_phone:
                            # به‌روزرسانی کل درآمد (تفاوت مبلغ جدید و قدیم)
                            current_income = int(p.get('total_income', 0) or 0)
                            diff_commission = commission_amount - old_commission
                            p['total_income'] = max(0, current_income + diff_commission)
                            
                            # به‌روزرسانی کل فروش‌های تایید شده (تفاوت مبلغ جدید و قدیم)
                            current_total_sales = int(p.get('total_approved_sales', 0) or 0)
                            diff_sale = sale - old_sale
                            p['total_approved_sales'] = max(0, current_total_sales + diff_sale)
                            
                            p['last_updated'] = iso_z(utcnow())
                            break
                    
                    save_express_partners(partners)
            except Exception as e:
                current_app.logger.error(f"Error updating partner stats after edit: {e}")
        
        flash('پورسانت با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('admin.express_commissions'))
    
    # GET - نمایش فرم ویرایش
    return render_template('admin/edit_commission.html', commission=commission)

# -----------------------------------------------------------------------------
# Express Partner Files (upload/list/download/delete by admin)
# -----------------------------------------------------------------------------
@admin_bp.route('/express/partner-files', methods=['GET', 'POST'])
@login_required
def express_partner_files():
    partners = load_express_partners() or []
    # Upload handler
    if request.method == 'POST':
        partner_phone = (request.form.get('partner_phone') or '').strip()
        f = request.files.get('file')
        if partner_phone and f and f.filename:
            base = os.path.join(current_app.instance_path, 'data', 'uploads', 'partner', partner_phone)
            os.makedirs(base, exist_ok=True)
            tsname = datetime.now().strftime('%Y%m%d%H%M%S%f') + "__" + secure_filename(f.filename)
            path = os.path.join(base, tsname)
            f.save(path)
            metas = load_partner_files_meta() or []
            new_id = (max([int(x.get('id',0) or 0) for x in metas if isinstance(x, dict)], default=0) or 0) + 1
            metas.append({
                'id': new_id,
                'phone': partner_phone,
                'filename': tsname,
                'stored_at': datetime.now().isoformat() + 'Z'
            })
            save_partner_files_meta(metas)
            flash('فایل بارگذاری شد.', 'success')
            return redirect(url_for('admin.express_partner_files', partner=partner_phone))

    # List
    try:
        partner_filter = (request.args.get('partner') or '').strip()
    except Exception:
        partner_filter = ''
    items = load_partner_files_meta() or []
    if partner_filter:
        items = [m for m in items if str(m.get('phone')) == partner_filter]
    try:
        items.sort(key=lambda x: x.get('stored_at',''), reverse=True)
    except Exception:
        pass
    return render_template('admin/express_partner_files.html', partners=partners, items=items, partner_filter=partner_filter)


@admin_bp.get('/express/partner-files/<int:fid>/download')
@login_required
def express_partner_file_download(fid: int):
    metas = load_partner_files_meta() or []
    meta = next((m for m in metas if int(m.get('id',0) or 0) == int(fid)), None)
    if not meta:
        abort(404)
    phone = str(meta.get('phone') or '').strip()
    base = os.path.join(current_app.instance_path, 'data', 'uploads', 'partner', phone)
    fp = os.path.join(base, meta.get('filename') or '')
    if not os.path.isfile(fp):
        abort(404)
    return send_from_directory(base, os.path.basename(fp), as_attachment=True)


@admin_bp.post('/express/partner-files/<int:fid>/delete')
@login_required
def express_partner_file_delete(fid: int):
    metas = load_partner_files_meta() or []
    kept = []
    removed = None
    for m in metas:
        try:
            if int(m.get('id',0) or 0) == int(fid):
                removed = m
            else:
                kept.append(m)
        except Exception:
            kept.append(m)
    save_partner_files_meta(kept)
    if removed:
        try:
            phone = str(removed.get('phone') or '').strip()
            base = os.path.join(current_app.instance_path, 'data', 'uploads', 'partner', phone)
            fp = os.path.join(base, removed.get('filename') or '')
            if os.path.isfile(fp):
                os.remove(fp)
        except Exception:
            pass
    flash('فایل حذف شد.', 'info')
    return redirect(url_for('admin.express_partner_files', partner=request.args.get('partner') or ''))

@admin_bp.post('/express/partners/applications/<int:aid>/approve')
@login_required
def express_partner_application_approve(aid: int):
    apps = load_express_partner_apps() or []
    partners = load_express_partners() or []
    target = None
    for a in apps:
        try:
            if int(a.get('id', 0)) == int(aid):
                target = a
                break
        except Exception:
            continue
    if not target:
        flash('درخواست یافت نشد.', 'warning')
        return redirect(url_for('admin.express_partner_applications'))

    # به فهرست همکاران منتقل و وضعیت را تنظیم کن
    phone = str(target.get('phone') or '').strip()
    name = (target.get('name') or '').strip()
    city = (target.get('city') or '').strip()
    partner = next((p for p in partners if str(p.get('phone')) == phone), None)
    if not partner:
        partner = {
            'id': (max([int(x.get('id',0) or 0) for x in partners], default=0) or 0) + 1,
            'name': name,
            'phone': phone,
            'city': city,
            'status': 'approved',
            'created_at': iso_z(utcnow()),
        }
        partners.append(partner)
    else:
        partner.update({'name': name or partner.get('name'), 'city': city or partner.get('city'), 'status': 'approved'})

    # وضعیت درخواست
    target['status'] = 'approved'
    target['approved_at'] = iso_z(utcnow())
    save_express_partners(partners)
    save_express_partner_apps(apps)

    # انتساب خودکار همه فایل‌های اکسپرس به همکار جدید
    try:
        lands = load_json(_lands_path()) or []
        express_lands = [l for l in lands if l.get('is_express', False)]
        assignments = load_express_assignments() or []
        
        # فایل‌هایی که قبلاً به این همکار انتساب نشده‌اند
        existing_codes = {a.get('land_code') for a in assignments if a.get('partner_phone') == phone}
        new_assignments_count = 0
        
        for land in express_lands:
            land_code = land.get('code')
            if land_code and land_code not in existing_codes:
                new_id = (max([int(x.get('id', 0) or 0) for x in assignments if isinstance(x, dict)], default=0) or 0) + 1
                assignments.append({
                    'id': new_id,
                    'partner_phone': phone,
                    'land_code': land_code,
                    'commission_pct': 2.0,  # درصد پیش‌فرض
                    'status': 'active',
                    'created_at': iso_z(utcnow())
                })
                new_assignments_count += 1
        
        if new_assignments_count > 0:
            save_express_assignments(assignments)
    except Exception as e:
        current_app.logger.error(f"Error auto-assigning lands to partner: {e}")

    # اعلان به کاربر
    try:
        if phone:
            add_notification(
                user_id=phone,
                title='تأیید همکاری وینور اکسپرس',
                body='درخواست شما تأیید شد. اکنون می‌توانید از پنل همکاری استفاده کنید.',
                ntype='success',
                action_url=url_for('express_partner.dashboard')
            )
    except Exception:
        pass

    if (request.headers.get('Accept') or '').lower().find('application/json') >= 0:
        return jsonify({ 'ok': True, 'id': int(aid), 'status': 'approved' })
    flash(f'درخواست تأیید شد و {new_assignments_count} فایل به همکار انتساب یافت.', 'success')
    return redirect(url_for('admin.express_partner_applications'))

@admin_bp.post('/express/partners/applications/<int:aid>/reject')
@login_required
def express_partner_application_reject(aid: int):
    apps = load_express_partner_apps() or []
    target = None
    for a in apps:
        try:
            if int(a.get('id', 0)) == int(aid):
                target = a
                break
        except Exception:
            continue
    if not target:
        flash('درخواست یافت نشد.', 'warning')
        return redirect(url_for('admin.express_partner_applications'))

    target['status'] = 'rejected'
    target['rejected_at'] = iso_z(utcnow())
    save_express_partner_apps(apps)

    # اعلان به کاربر
    try:
        phone = str(target.get('phone') or '')
        if phone:
            add_notification(
                user_id=phone,
                title='رد درخواست همکاری وینور اکسپرس',
                body='درخواست شما در حال حاضر تأیید نشد.',
                ntype='warning',
                action_url=url_for('express_partner.apply')
            )
    except Exception:
        pass

    if (request.headers.get('Accept') or '').lower().find('application/json') >= 0:
        return jsonify({ 'ok': True, 'id': int(aid), 'status': 'rejected' })
    flash('درخواست رد شد.', 'info')
    return redirect(url_for('admin.express_partner_applications'))


# ─────────────────────────────────────────────────────────────────────────────
# مدیریت شهرهای فعال برای همکاری
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/express/cities', methods=['GET', 'POST'])
@login_required
def express_cities():
    """مدیریت شهرهای فعال برای درخواست همکاری"""
    cities = load_active_cities() or []
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            new_city = (request.form.get('city') or '').strip()
            if new_city and new_city not in cities:
                cities.append(new_city)
                cities.sort()
                save_active_cities(cities)
                flash(f'شهر "{new_city}" اضافه شد.', 'success')
            elif new_city in cities:
                flash('این شهر قبلاً اضافه شده است.', 'warning')
        
        elif action == 'delete':
            city_to_delete = request.form.get('city')
            if city_to_delete in cities:
                cities.remove(city_to_delete)
                save_active_cities(cities)
                flash(f'شهر "{city_to_delete}" حذف شد.', 'info')
        
        return redirect(url_for('admin.express_cities'))
    
    return render_template('admin/express_cities.html', cities=cities)
