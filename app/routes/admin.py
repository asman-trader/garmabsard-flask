# app/admin/routes.py
# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
from functools import wraps
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime
import requests

# اگر CSRFProtect را در app factory فعال کرده‌اید، می‌توانیم موقتاً فقط روی روت لاگین غیرفعالش کنیم
try:
    from flask_wtf.csrf import csrf  # LocalProxy
except Exception:
    csrf = None  # اگر Flask-WTF موجود نبود، معاف‌سازی CSRF را انجام نمی‌دهیم

admin_bp = Blueprint('admin', __name__)

# ====== پیکربندی ساده ادمین (برای شروع) ======
# بعد از اولین ورود، حتماً رمز را تغییر دهید یا به سیستم کاربر/نقش مهاجرت کنید.
ADMIN_USERNAME = 'masood1528014@gmail.com'
ADMIN_PASSWORD = 'm430128185'

# ---------- ابزار پیامک OTP (برای توسعه‌های بعدی آماده است) ----------
def send_otp_sms(phone, code):
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
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}
    return response.status_code, body

# ---------- توابع کمکی JSON ----------
def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- مسیرها با fallback ایمن روی instance/data ----------
def _settings_path():
    # اگر در app.config ست شده باشد همان را استفاده کن؛
    # در غیر اینصورت روی instance/data/settings.json ذخیره می‌کند.
    return current_app.config.get(
        'SETTINGS_FILE',
        os.path.join(current_app.instance_path, 'data', 'settings.json')
    )

def _lands_path():
    return current_app.config.get(
        "LANDS_FILE",
        os.path.join(current_app.instance_path, "data", "lands.json")
    )

def _consults_path():
    return current_app.config.get(
        "CONSULTS_FILE",
        os.path.join(current_app.instance_path, "data", "consults.json")
    )

def get_settings():
    settings_file = _settings_path()
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {'approval_method': 'manual'}

# ---------- دکوراتور لاگین ----------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin.login'))
        return view(*args, **kwargs)
    return wrapper

# ---------- احراز هویت ----------
@admin_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    """
    نکته امنیتی:
    - در تمپلیت admin/login.html حتماً CSRF token بگذارید:
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    - تا قبل از اضافه شدن توکن در فرم، می‌توانید موقتاً این روت را CSRF-exempt کنید
      (چند خط پایین‌تر انجام شده). بعد از اصلاح تمپلیت، آن را بردارید.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('خوش آمدید؛ ورود موفق.', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    return render_template('admin/login.html')

# اگر CSRF فعال است، فقط همین روت لاگین را موقتاً معاف کن (برای عبور از خطای CSRF در مرحله تست)
# مهم: پس از افزودن توکن CSRF در فرم لاگین، این خط را کامنت/حذف کنید.
if csrf is not None:
    admin_bp.view_functions['login'] = csrf.exempt(admin_bp.view_functions['login'])

@admin_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('logged_in', None)
    flash('خروج انجام شد.', 'info')
    return redirect(url_for('admin.login'))

# ---------- داشبورد ----------
@admin_bp.route('/')
@login_required
def dashboard():
    lands = load_json(_lands_path())
    consults = load_json(_consults_path())
    return render_template('admin/dashboard.html',
                           lands_count=len(lands),
                           consults_count=len(consults))

# ---------- آگهی‌ها ----------
@admin_bp.route('/lands')
@login_required
def lands():
    lands = load_json(_lands_path())
    return render_template('admin/lands.html', lands=lands)

@admin_bp.route('/consults')
@login_required
def consults():
    consults = load_json(_consults_path())
    lands = load_json(_lands_path())
    land_map = {str(l.get('code')): l for l in lands}
    for c in consults:
        c['land'] = land_map.get(str(c.get('code')))
    return render_template('admin/consults.html', consults=consults)

@admin_bp.route('/lands/add', methods=['GET', 'POST'])
@login_required
def add_land():
    if request.method == 'POST':
        form = request.form
        images = request.files.getlist('images')

        settings = get_settings()
        approval_method = settings.get('approval_method', 'manual')
        status = 'approved' if approval_method == 'auto' else 'pending'

        lands = load_json(_lands_path())
        existing_codes = [int(l['code']) for l in lands if 'code' in l and str(l['code']).isdigit()]
        new_code = str(max(existing_codes) + 1) if existing_codes else '100'

        # مسیر آپلود
        upload_folder = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        image_urls = []
        for image in images:
            if image and image.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}__{image.filename}")
                image.save(os.path.join(upload_folder, filename))
                image_urls.append(f"uploads/{filename}")

        lands.append({
            'title': form.get('title', '').strip(),
            'size': form.get('size', '').strip(),
            'location': form.get('location', '').strip(),
            'code': new_code,
            'category': form.get('category', '').strip(),
            'document_type': form.get('document_type', '').strip(),
            'description': form.get('description', '').strip(),
            'features': form.getlist('features'),
            'price_total': form.get('price_total', '').strip(),
            'price_per_meter': form.get('price_per_meter', '').strip(),
            'images': image_urls,
            'approval_method': approval_method,
            'status': status,
            'created_at': datetime.now().strftime('%Y-%m-%d')
        })

        save_json(_lands_path(), lands)
        flash(f'آگهی با کد {new_code} با موفقیت ثبت شد.', 'success')
        return redirect(url_for('admin.lands'))

    return render_template('admin/add-land.html')

@admin_bp.route('/edit-land/<int:land_id>', methods=['GET', 'POST'])
@login_required
def edit_land(land_id):
    lands = load_json(_lands_path())
    if land_id < 0 or land_id >= len(lands):
        flash('آگهی مورد نظر پیدا نشد.', 'warning')
        return redirect(url_for('admin.lands'))

    land = lands[land_id]

    if request.method == 'POST':
        form = request.form
        land.update({
            'title': form.get('title', '').strip(),
            'size': form.get('size', '').strip(),
            'location': form.get('location', '').strip(),
            'code': form.get('code', str(land.get('code', ''))).strip(),
            'category': form.get('category', '').strip(),
            'document_type': form.get('document_type', '').strip(),
            'description': form.get('description', '').strip(),
            'features': form.getlist('features'),
            'price_total': form.get('price_total', '').strip(),
            'price_per_meter': form.get('price_per_meter', '').strip(),
            'approval_method': form.get('approval_method', land.get('approval_method', 'manual'))
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

        # آپلود تصاویر جدید
        new_images = request.files.getlist('images')
        upload_folder = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        for image in new_images:
            if image and image.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}__{image.filename}")
                image.save(os.path.join(upload_folder, filename))
                land.setdefault('images', []).append(f'uploads/{filename}')

        save_json(_lands_path(), lands)
        flash('آگهی با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('admin.lands'))

    return render_template('admin/edit-land.html', land=land, land_id=land_id)

@admin_bp.route('/delete-land/<int:land_id>', methods=['POST'])
@login_required
def delete_land(land_id):
    lands = load_json(_lands_path())
    if land_id < 0 or land_id >= len(lands):
        flash('آگهی مورد نظر پیدا نشد.', 'warning')
        return redirect(url_for('admin.lands'))

    land = lands.pop(land_id)
    for img in land.get('images', []):
        path = os.path.join(current_app.static_folder, img)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    save_json(_lands_path(), lands)
    flash('آگهی با موفقیت حذف شد.', 'success')
    return redirect(url_for('admin.lands'))

# ---------- وضعیت‌ها ----------
@admin_bp.route('/pending-lands')
@login_required
def pending_lands():
    lands = load_json(_lands_path())
    return render_template('admin/pending-lands.html',
                           lands=[l for l in lands if l.get('status') == 'pending'])

@admin_bp.route('/approved-lands')
@login_required
def approved_lands():
    lands = load_json(_lands_path())
    return render_template('admin/pending-lands.html',
                           lands=[l for l in lands if l.get('status') == 'approved'])

@admin_bp.route('/rejected-lands')
@login_required
def rejected_lands():
    lands = load_json(_lands_path())
    return render_template('admin/pending-lands.html',
                           lands=[l for l in lands if l.get('status') == 'rejected'])

# ---------- تایید و رد ----------
@admin_bp.route('/approve-land/<code>', methods=['POST'])
@login_required
def approve_land(code):
    lands = load_json(_lands_path())
    updated = False
    for land in lands:
        if str(land.get('code')) == str(code):
            land['status'] = 'approved'
            updated = True
            break
    save_json(_lands_path(), lands)
    flash('آگهی تأیید شد.' if updated else 'آگهی یافت نشد.', 'success' if updated else 'warning')
    return redirect(url_for('admin.pending_lands'))

@admin_bp.route('/reject-land/<code>', methods=['POST'])
@login_required
def reject_land(code):
    lands = load_json(_lands_path())
    updated = False
    for land in lands:
        if str(land.get('code')) == str(code):
            land['status'] = 'rejected'
            updated = True
            break
    save_json(_lands_path(), lands)
    flash('آگهی رد شد.' if updated else 'آگهی یافت نشد.', 'info' if updated else 'warning')
    return redirect(url_for('admin.pending_lands'))

# ---------- تنظیمات ----------
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings_file = _settings_path()

    if request.method == 'POST':
        approval_method = request.form.get('approval_method', 'manual')
        save_json(settings_file, {'approval_method': approval_method})
        flash('تنظیمات با موفقیت ذخیره شد.', 'success')
        return redirect(url_for('admin.settings'))

    settings_data = get_settings()
    return render_template('admin/settings.html', settings=settings_data)
