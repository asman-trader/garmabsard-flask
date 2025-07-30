from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime
import requests

admin_bp = Blueprint('admin', __name__)
ADMIN_USERNAME = 'masood1528014@gmail.com'
ADMIN_PASSWORD = 'm430128185'

# ---------- ابزارها ----------
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
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.json()

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_settings():
    settings_file = os.path.join('data', 'settings.json')
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {'approval_method': 'manual'}

# ---------- احراز هویت ----------
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است.')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin.login'))

# ---------- داشبورد ----------
@admin_bp.route('/')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    consults = load_json(current_app.config['CONSULTS_FILE'])
    return render_template('admin/dashboard.html', lands_count=len(lands), consults_count=len(consults))

# ---------- آگهی‌ها ----------
@admin_bp.route('/lands')
def lands():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    return render_template('admin/lands.html', lands=lands)

@admin_bp.route('/consults')
def consults():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    consults = load_json(current_app.config['CONSULTS_FILE'])
    lands = load_json(current_app.config['LANDS_FILE'])
    land_map = {l.get('code'): l for l in lands}
    for c in consults:
        c['land'] = land_map.get(c.get('code'))
    return render_template('admin/consults.html', consults=consults)

@admin_bp.route('/lands/add', methods=['GET', 'POST'])
def add_land():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        form = request.form
        images = request.files.getlist('images')

        settings = get_settings()
        approval_method = settings.get('approval_method', 'manual')
        status = 'approved' if approval_method == 'auto' else 'pending'

        lands = load_json(current_app.config['LANDS_FILE'])
        existing_codes = [int(l['code']) for l in lands if 'code' in l and str(l['code']).isdigit()]
        new_code = str(max(existing_codes) + 1) if existing_codes else '100'

        image_urls = []
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        for image in images:
            if image and image.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}__{image.filename}")
                image.save(os.path.join(upload_folder, filename))
                image_urls.append(f"uploads/{filename}")

        lands.append({
            'title': form.get('title'),
            'size': form.get('size'),
            'location': form.get('location'),
            'code': new_code,
            'category': form.get('category'),
            'document_type': form.get('document_type'),
            'description': form.get('description'),
            'features': form.getlist('features'),
            'price_total': form.get('price_total'),
            'price_per_meter': form.get('price_per_meter'),
            'images': image_urls,
            'approval_method': approval_method,
            'status': status,
            'created_at': datetime.now().strftime('%Y-%m-%d')
        })
        save_json(current_app.config['LANDS_FILE'], lands)
        flash(f'آگهی با کد {new_code} با موفقیت ثبت شد.')
        return redirect(url_for('admin.lands'))

    return render_template('admin/add-land.html')

@admin_bp.route('/edit-land/<int:land_id>', methods=['GET', 'POST'])
def edit_land(land_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))

    lands = load_json(current_app.config['LANDS_FILE'])
    if land_id < 0 or land_id >= len(lands):
        flash('آگهی مورد نظر پیدا نشد.')
        return redirect(url_for('admin.lands'))

    land = lands[land_id]
    if request.method == 'POST':
        form = request.form
        land.update({
            'title': form.get('title'),
            'size': form.get('size'),
            'location': form.get('location'),
            'code': form.get('code'),
            'category': form.get('category'),
            'document_type': form.get('document_type'),
            'description': form.get('description'),
            'features': form.getlist('features'),
            'price_total': form.get('price_total'),
            'price_per_meter': form.get('price_per_meter'),
            'approval_method': form.get('approval_method', 'manual')
        })

        if request.form.get('remove_all_images') == 'on':
            for img in land.get('images', []):
                path = os.path.join(current_app.root_path, 'static', img)
                if os.path.exists(path):
                    os.remove(path)
            land['images'] = []

        new_images = request.files.getlist('images')
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        for image in new_images:
            if image and image.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}__{image.filename}")
                image.save(os.path.join(upload_folder, filename))
                land.setdefault('images', []).append(f'uploads/{filename}')

        save_json(current_app.config['LANDS_FILE'], lands)
        flash('آگهی با موفقیت ویرایش شد.')
        return redirect(url_for('admin.lands'))

    return render_template('admin/edit-land.html', land=land, land_id=land_id)

@admin_bp.route('/delete-land/<int:land_id>')
def delete_land(land_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))

    lands = load_json(current_app.config['LANDS_FILE'])
    if land_id < 0 or land_id >= len(lands):
        flash('آگهی مورد نظر پیدا نشد.')
        return redirect(url_for('admin.lands'))

    land = lands.pop(land_id)
    for img in land.get('images', []):
        path = os.path.join(current_app.root_path, 'static', img)
        if os.path.exists(path):
            os.remove(path)

    save_json(current_app.config['LANDS_FILE'], lands)
    flash('آگهی با موفقیت حذف شد.')
    return redirect(url_for('admin.lands'))

# ---------- وضعیت‌ها ----------
@admin_bp.route('/pending-lands')
def pending_lands():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    return render_template('admin/pending-lands.html', lands=[l for l in lands if l.get('status') == 'pending'])

@admin_bp.route('/approved-lands')
def approved_lands():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    return render_template('admin/pending-lands.html', lands=[l for l in lands if l.get('status') == 'approved'])

@admin_bp.route('/rejected-lands')
def rejected_lands():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    return render_template('admin/pending-lands.html', lands=[l for l in lands if l.get('status') == 'rejected'])

# ---------- تایید و رد ----------
@admin_bp.route('/approve-land/<code>', methods=['POST'])
def approve_land(code):
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    for land in lands:
        if land.get('code') == code:
            land['status'] = 'approved'
            break
    save_json(current_app.config['LANDS_FILE'], lands)
    flash('آگهی تأیید شد.')
    return redirect(url_for('admin.pending_lands'))

@admin_bp.route('/reject-land/<code>')
def reject_land(code):
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))
    lands = load_json(current_app.config['LANDS_FILE'])
    for land in lands:
        if land.get('code') == code:
            land['status'] = 'rejected'
            break
    save_json(current_app.config['LANDS_FILE'], lands)
    flash('آگهی رد شد.')
    return redirect(url_for('admin.pending_lands'))

# ---------- تنظیمات ----------
@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('admin.login'))

    settings_file = os.path.join('data', 'settings.json')

    if request.method == 'POST':
        approval_method = request.form.get('approval_method', 'manual')
        save_json(settings_file, {'approval_method': approval_method})
        flash('تنظیمات با موفقیت ذخیره شد.')
        return redirect(url_for('admin.settings'))

    settings_data = get_settings()
    return render_template('admin/settings.html', settings=settings_data)
