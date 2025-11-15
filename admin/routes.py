# app/admin/routes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import List, Dict, Any, Optional

from flask import (
    render_template, request, redirect, url_for,
    session, current_app, flash, abort, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename

# اختیاری: ارسال OTP برای توسعه‌های بعدی
import requests
import time

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
from app.utils.storage import load_users, load_reports, save_reports, load_consultant_apps, save_consultant_apps, load_consultants, save_consultants, save_ads
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
# ابزار پیامک OTP (رزرو برای آینده)
# -----------------------------------------------------------------------------
def send_otp_sms(phone: str, code: str):
    url = "https://api.sms.ir/v1/send/verify"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-KEY": "cwDc9dmxkF4c1avGDTBFnlRPyJQkxk2TVhpZCj6ShGrVx9y4"
    }
    payload = {
        "mobile": phone,
        "templateId": 753422,
        "parameters": [{"name": "CODE", "value": str(code)}]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        body = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else {"raw": response.text}
        return response.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}

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

def _consults_path() -> str:
    return current_app.config.get(
        "CONSULTS_FILE",
        os.path.join(current_app.instance_path, "data", "consults.json")
    )

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
            flash('خوش آمدید؛ ورود موفق.', 'success')
            return redirect(url_for('admin.express_hub'))
        flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    return render_template('admin/login.html')

# معافیت موقت CSRF فقط برای لاگین (پس از افزودن توکن، این را حذف کنید)
if csrf is not None:
    admin_bp.view_functions['login'] = csrf.exempt(admin_bp.view_functions['login'])

@admin_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('logged_in', None)
    flash('خروج انجام شد.', 'info')
    return redirect(url_for('admin.login'))

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

## admin consults removed

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
    return str(max(existing_codes) + 1) if existing_codes else '100'

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

@admin_bp.route('/express/hub', endpoint='express_hub')
@login_required
def express_hub():
    """مرکز مدیریت اکسپرس: لینک‌های سریع + اکشن انتقال داده."""
    return render_template('admin/express_hub.html')

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
    return redirect(url_for('admin.express_hub'))

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
        size = form.get('size', '').strip()
        price_total = form.get('price_total', '').strip()
        
        if not all([title, location, size, price_total]):
            flash('لطفاً فیلدهای اجباری را پر کنید.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        
        if len(title) < 10:
            flash('عنوان باید حداقل ۱۰ کاراکتر باشد.', 'error')
            return render_template('admin/add_express_listing.html',
                                  pending_count=0, approved_count=0, rejected_count=0)
        
        # تولید کد منحصر به فرد
        new_code = datetime.now().strftime('%Y%m%d%H%M%S')
        
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
        
        # کمیسیون همکاران (اختیاری)
        pct_raw = (form.get('express_commission_pct') or '').strip()
        try:
            express_commission_pct = float(pct_raw) if pct_raw else None
        except Exception:
            express_commission_pct = None
        try:
            price_int = int(price_total)
        except Exception:
            price_int = 0
        express_commission_amount = int(round(price_int * ((express_commission_pct or 0)/100.0))) if price_int and (express_commission_pct is not None) else None

        # ایجاد آگهی اکسپرس
        new_express_land = {
            'code': new_code,
            'title': title,
            'location': location,
            'size': size,
            'price_total': int(price_total),
            'price_per_meter': int(form.get('price_per_meter', 0) or 0),
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
        
        # ذخیره در فایل
        lands = load_json(_lands_path())
        lands.append(new_express_land)
        save_ads(lands)
        
        # ارسال نوتیفیکیشن به کاربران منطقه
        _send_express_notification(new_express_land)

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

def _send_express_notification(express_land):
    """ارسال نوتیفیکیشن برای آگهی اکسپرس جدید"""
    try:
        location = express_land.get('location', '')
        title = express_land.get('title', '')
        
        message = f"🏠 ملک تأییدشده جدید در {location} - وینور اکسپرس"
        
        # ارسال نوتیفیکیشن به کاربران منطقه
        add_notification(
            title="ملک تأییدشده جدید",
            message=message,
            notification_type="express_listing",
            data={
                "land_code": express_land.get('code'),
                "location": location,
                "title": title
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error sending express notification: {e}")

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
# Push/SMS routes moved to dedicated modules


# -----------------------------------------------------------------------------
# Consultants: Applications & List (MVP)
# -----------------------------------------------------------------------------
## روت‌های مربوط به درخواست‌های مشاورین حذف شدند

## روت فهرست مشاورین حذف شد

# -----------------------------------------------------------------------------
# Consultants: Approve / Reject applications
# -----------------------------------------------------------------------------
## روت تایید درخواست مشاور حذف شد

## روت رد درخواست مشاور حذف شد

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
        items = load_express_partners() or []
        if not isinstance(items, list):
            items = []
    except Exception:
        items = []
    return render_template('admin/express_partners.html', items=items)

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
    # partners list for quick assignment
    partners = load_express_partners() or []
    # lands pool
    lands = load_json(_lands_path()) or []
    express_pool = [l for l in lands if l.get('is_express', False) and str(l.get('status')) == 'approved']
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
    for c in items:
        try:
            if int(c.get('id',0) or 0) == int(cid):
                c['status'] = 'approved'
                c['approved_at'] = iso_z(utcnow())
                changed = True
                break
        except Exception:
            continue
    if changed:
        save_express_commissions(items)
        flash('پورسانت تایید شد.', 'success')
    return redirect(url_for('admin.express_commissions'))

@admin_bp.post('/express/commissions/<int:cid>/pay')
@login_required
def express_commission_pay(cid: int):
    items = load_express_commissions() or []
    changed = False
    for c in items:
        try:
            if int(c.get('id',0) or 0) == int(cid):
                c['status'] = 'paid'
                c['paid_at'] = iso_z(utcnow())
                changed = True
                break
        except Exception:
            continue
    if changed:
        save_express_commissions(items)
        flash('پورسانت پرداخت شد.', 'success')
    return redirect(url_for('admin.express_commissions'))

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
    flash('درخواست تأیید شد و کاربر به همکاران اکسپرس افزوده شد.', 'success')
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
