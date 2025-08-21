from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
import os, json, random, requests, subprocess, shutil
from datetime import datetime
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)
SMS_API_KEY = "cwDc9dmxkF4c1avGDTBFnlRPyJQkxk2TVhpZCj6ShGrVx9y4"

# ---------------- دسته‌بندی‌ها: کلید ↔ برچسب ----------------
CATEGORY_MAP = {
    "": "همه آگهی‌ها",
    "residential_land": "زمین مسکونی",
    "garden": "باغ",
    "villa": "ویلا",
    "titled": "سنددار",
    "with_utilities": "دارای آب و برق",
    "good_price": "قیمت مناسب"
}
CATEGORY_KEYS = set(CATEGORY_MAP.keys()) - {""}

# ================== مسیرهای Production-safe (instance/data) ==================
def _data_dir(app=None):
    """
    مسیر امن و قابل‌نوشتن روی هاست: <instance>/data
    اگر app پاس شود، از همان استفاده می‌شود تا خارج از context هم کار کند.
    """
    app = app or current_app
    base = app.instance_path
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, 'data')
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, 'uploads'), exist_ok=True)  # uploads/
    return path

def _legacy_data_dir(app=None):
    """مسیر قدیمی داخل کُد (ممکن است read-only باشد)"""
    app = app or current_app
    return os.path.join(app.root_path, 'data')

def _ensure_file(config_key: str, filename: str, default_content, app=None):
    """
    اگر config_key ست نشده باشد یا فایل وجود نداشته باشد:
      - مسیر پیش‌فرض instance/data/<filename> ساخته می‌شود
      - در صورت نبود، فایل با default_content ایجاد می‌شود
      - اگر نسخهٔ قدیمی در data/ باشد، مهاجرت می‌شود
    """
    app = app or current_app
    data_dir = _data_dir(app)
    fpath = app.config.get(config_key) or os.path.join(data_dir, filename)
    app.config[config_key] = fpath

    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    if not os.path.exists(fpath):
        legacy = os.path.join(_legacy_data_dir(app), filename)
        if os.path.exists(legacy):
            try:
                shutil.copy2(legacy, fpath)
            except Exception:
                pass
        if not os.path.exists(fpath):
            with open(fpath, 'w', encoding='utf-8') as f:
                if isinstance(default_content, (dict, list)):
                    json.dump(default_content, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(default_content or ""))
    return fpath

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

# ---------------- ابزارهای کمکی داده ----------------
def parse_datetime_safe(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except Exception:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return datetime(1970, 1, 1)

def _to_int(x, default=0):
    try:
        return int(str(x).replace(',', '').strip())
    except Exception:
        return default

def load_ads(app=None):
    path = _ensure_file('LANDS_FILE', 'lands.json', [], app)
    return load_json(path)

def save_ads(items, app=None):
    path = _ensure_file('LANDS_FILE', 'lands.json', [], app)
    save_json(path, items)

def load_users(app=None):
    path = _ensure_file('USERS_FILE', 'users.json', [], app)
    return load_json(path)

def save_users(items, app=None):
    path = _ensure_file('USERS_FILE', 'users.json', [], app)
    save_json(path, items)

def load_consults(app=None):
    path = _ensure_file('CONSULTS_FILE', 'consults.json', [], app)
    return load_json(path)

def save_consults(items, app=None):
    path = _ensure_file('CONSULTS_FILE', 'consults.json', [], app)
    save_json(path, items)

def load_settings(app=None):
    path = _ensure_file('SETTINGS_FILE', 'settings.json', {"approval_method": "manual"}, app)
    return load_json(path)

def get_land_by_code(code):
    lands = load_ads()
    return next((l for l in lands if l.get('code') == code), None)

# ---------------- مهاجرت فایل‌های قدیمی + آماده‌سازی ----------------
def _migrate_legacy(app=None):
    """
    اگر فایل‌های قدیمی داخل root_path/data باشند و در instance/data نباشند،
    به instance/data کپی می‌شوند. uploads نیز در صورت وجود، مهاجرت می‌شود.
    """
    app = app or current_app
    inst = _data_dir(app)
    legacy = _legacy_data_dir(app)
    try:
        # JSON ها
        for name in ('lands.json', 'users.json', 'consults.json', 'settings.json', 'notifications.json'):
            old = os.path.join(legacy, name)
            new = os.path.join(inst, name)
            if os.path.exists(old) and not os.path.exists(new):
                try:
                    shutil.copy2(old, new)
                except Exception:
                    pass
        # uploads
        old_up = os.path.join(legacy, 'uploads')
        new_up = os.path.join(inst, 'uploads')
        if os.path.isdir(old_up):
            if not os.path.exists(new_up) or (os.path.exists(new_up) and not os.listdir(new_up)):
                try:
                    shutil.copytree(old_up, new_up, dirs_exist_ok=True)
                except Exception:
                    pass
    except Exception as e:
        try:
            app.logger.warning("Legacy migration issue: %s", e)
        except Exception:
            pass

@main_bp.record_once
def _on_bp_loaded(setup_state):
    app = setup_state.app
    _ = _data_dir(app)
    _migrate_legacy(app)
    _ensure_file('LANDS_FILE', 'lands.json', [], app)
    _ensure_file('USERS_FILE', 'users.json', [], app)
    _ensure_file('CONSULTS_FILE', 'consults.json', [], app)
    _ensure_file('SETTINGS_FILE', 'settings.json', {"approval_method": "manual"}, app)
    _ensure_file('NOTIFICATIONS_FILE', 'notifications.json', [], app)

# ---------------- فیلتر تاریخ جینجا: از خطای strftime جلوگیری می‌کند ----------------
def _parse_any_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                pass
    return None

@main_bp.app_template_filter("date_ymd")
def date_ymd(value, default="-"):
    dt = _parse_any_date(value)
    if dt:
        return dt.strftime("%Y/%m/%d")
    if isinstance(value, str) and value:
        return value.split(" ")[0].replace("-", "/")
    return default

# ---------------- ارسال OTP ----------------
def send_sms_code(phone, code):
    url = "https://api.sms.ir/v1/send/verify"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": SMS_API_KEY
    }
    data = {
        "mobile": phone,
        "templateId": 753422,
        "parameters": [{"name": "code", "value": code}]
    }
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except Exception as e:
        try:
            current_app.logger.error("❌ خطا در ارسال پیامک: %s", e)
        except Exception:
            print("❌ خطا در ارسال پیامک:", e)

# ---------------- وب‌هوک Pull اتوماتیک ----------------
@main_bp.route('/git-webhook', methods=['POST'])
def git_webhook():
    try:
        repo_path = os.path.abspath('.')
        subprocess.run(['git', '-C', repo_path, 'pull'], check=True)
        return '✅ کد جدید دریافت شد.', 200
    except Exception as e:
        return f'❌ خطا در Pull: {str(e)}', 500

# ---------------- صفحه اصلی ----------------
@main_bp.route('/')
def index():
    lands = load_ads()
    approved = [l for l in lands if l.get('status') == 'approved']
    sorted_lands = sorted(
        approved,
        key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')),
        reverse=True
    )
    return render_template('index.html', lands=sorted_lands, now=datetime.now(), CATEGORY_MAP=CATEGORY_MAP)

# ---------------- جزئیات آگهی ----------------
@main_bp.route('/land/<code>')
def land_detail(code):
    land = get_land_by_code(code)
    if not land:
        return "زمین پیدا نشد", 404
    return render_template('land_detail.html', land=land, now=datetime.now(), CATEGORY_MAP=CATEGORY_MAP)

# ---------------- سرو فایل‌های آپلود ----------------
@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    ابتدا از instance/data/uploads سرو می‌کنیم؛ اگر نبود، از مسیر قدیمی root_path/data/uploads.
    """
    cand = [
        os.path.join(_data_dir(), 'uploads'),
        os.path.join(_legacy_data_dir(), 'uploads')
    ]
    for folder in cand:
        fpath = os.path.join(folder, filename)
        if os.path.exists(fpath):
            return send_from_directory(folder, filename)
    return "File not found", 404

# ---------------- ثبت درخواست مشاوره ----------------
@main_bp.route('/consult/<code>', methods=['POST'])
def consult(code):
    consults = load_consults()
    consults.append({
        'name': request.form.get('name'),
        'phone': request.form.get('phone'),
        'message': request.form.get('message'),
        'code': code,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_consults(consults)
    flash("✅ درخواست مشاوره ثبت شد.")
    return redirect(url_for('main.land_detail', code=code))

# ---------------- ورود با OTP ----------------
@main_bp.route('/login', methods=['GET', 'POST'])
def send_otp():
    if request.method == 'POST':
        phone = request.form.get('phone')
        if not phone:
            flash("شماره موبایل الزامی است.")
            return redirect(url_for('main.send_otp'))
        code = str(random.randint(10000, 99999))
        session.update({'otp_code': code, 'otp_phone': phone})
        send_sms_code(phone, code)
        return render_template('login_step2.html', phone=phone)
    return render_template('login_step1.html')

@main_bp.route('/verify', methods=['POST'])
def verify_otp():
    code = request.form.get('otp_code')
    phone = request.form.get('phone')
    if not code or not phone:
        flash("اطلاعات ناقص است.")
        return redirect(url_for('main.send_otp'))

    if session.get('otp_code') == code and session.get('otp_phone') == phone:
        session['user_phone'] = phone
        users = load_users()
        if not any(u.get('phone') == phone for u in users):
            users.append({'phone': phone, 'registered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            save_users(users)
        flash("✅ ورود موفقیت‌آمیز بود.")
        return redirect(session.pop('next', None) or url_for('main.index'))
    flash("❌ کد واردشده نادرست است.")
    return redirect(url_for('main.send_otp'))

@main_bp.route('/logout')
def logout():
    session.pop('user_phone', None)
    flash("از حساب خارج شدید.")
    return redirect(url_for('main.index'))

# ---------------- ثبت آگهی (مرحله 1 + 2) ----------------
@main_bp.route('/submit-ad', methods=['GET', 'POST'])
def submit_ad():
    return redirect(url_for('main.add_land'))

@main_bp.route('/lands/add', methods=['GET', 'POST'])
def add_land():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land')
        return redirect(url_for('main.send_otp'))

    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        size = request.form.get('size')
        price_total = request.form.get('price_total') or None
        description = request.form.get('description')
        category = request.form.get('category', '').strip()
        if category and category not in CATEGORY_KEYS:
            category = ""

        images = request.files.getlist('images')

        if not title or not location or not size:
            flash("همه فیلدها الزامی هستند.")
            return redirect(url_for('main.add_land'))

        code = datetime.now().strftime('%Y%m%d%H%M%S')
        upload_dir = os.path.join(_data_dir(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        image_names = []

        for img in images:
            if img and img.filename:
                fname = f"{code}__{secure_filename(img.filename)}"
                img.save(os.path.join(upload_dir, fname))
                image_names.append(fname)

        session.update({
            'land_code': code,
            'land_temp': {
                'title': title,
                'location': location,
                'size': size,
                'price_total': _to_int(price_total) if price_total else None,
                'description': description,
                'category': category
            },
            'land_images': image_names
        })
        return redirect(url_for('main.add_land_step3'))

    return render_template('add_land.html', CATEGORY_MAP=CATEGORY_MAP)

# ---------------- ثبت آگهی (مرحله 3: انتخاب نوع) ----------------
@main_bp.route('/lands/add/step3', methods=['GET', 'POST'])
def add_land_step3():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land_step3')
        return redirect(url_for('main.send_otp'))

    if request.method == 'POST':
        ad_type = request.form.get('ad_type')
        if ad_type not in ['site', 'broadcast']:
            flash("نوع آگهی نامعتبر است.")
            return redirect(url_for('main.add_land_step3'))

        session['land_ad_type'] = ad_type
        return redirect(url_for('main.finalize_land'))

    return render_template('add_land_step3.html')

# ---------------- نهایی‌سازی ثبت آگهی ----------------
@main_bp.route('/lands/finalize')
def finalize_land():
    keys = ['land_code', 'land_temp', 'land_images', 'land_ad_type']
    if not all(k in session for k in keys):
        flash("اطلاعات ناقص است.")
        return redirect(url_for('main.add_land'))

    settings = load_settings()
    approval_method = settings.get('approval_method', 'manual')
    status = 'approved' if approval_method == 'auto' else 'pending'

    lands = load_ads()
    lt = session['land_temp']
    new_land = {
        'code': session['land_code'],
        'title': lt['title'],
        'location': lt['location'],
        'size': lt['size'],
        'price_total': lt['price_total'],
        'description': lt.get('description'),
        'images': session['land_images'],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'owner': session.get('user_phone'),
        'status': status,
        'ad_type': session['land_ad_type'],
        'category': lt.get('category', '')
    }

    lands.append(new_land)
    save_ads(lands)
    for k in keys:
        session.pop(k, None)

    msg = "✅ آگهی شما با موفقیت ثبت شد." + (" به صورت خودکار منتشر شد." if status == 'approved' else " و در انتظار تأیید قرار گرفت.")
    flash(msg)
    return redirect(url_for('main.my_lands'))

# ---------------- آگهی‌های من (جستجو/فیلتر/سورت/صفحه‌بندی) ----------------
@main_bp.route('/my-lands')
def my_lands():
    if 'user_phone' not in session:
        flash("برای مشاهده آگهی‌ها وارد شوید.")
        session['next'] = url_for('main.my_lands')
        return redirect(url_for('main.send_otp'))

    q        = (request.args.get('q') or '').strip().lower()
    status   = (request.args.get('status') or '').strip()
    sort     = (request.args.get('sort') or 'new').strip()
    page     = int(request.args.get('page', 1) or 1)
    per_page = min(int(request.args.get('per_page', 12) or 12), 48)

    lands_all = load_ads()
    user_lands = [l for l in lands_all if l.get('owner') == session['user_phone']]

    if status in {'approved', 'pending', 'rejected'}:
        user_lands = [l for l in user_lands if l.get('status') == status]

    if q:
        def _hit(ad):
            title = (ad.get('title') or '').lower()
            loc   = (ad.get('location') or '').lower()
            desc  = (ad.get('description') or '').lower()
            code  = str(ad.get('code') or '')
            return (q in title) or (q in loc) or (q in desc) or (q == code)
        user_lands = [ad for ad in user_lands if _hit(ad)]

    if sort == 'old':
        user_lands.sort(key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')))
    elif sort == 'size_desc':
        user_lands.sort(key=lambda x: _to_int(x.get('size')), reverse=True)
    elif sort == 'size_asc':
        user_lands.sort(key=lambda x: _to_int(x.get('size')))
    else:  # new
        user_lands.sort(key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)

    total = len(user_lands)
    pages = max((total - 1) // per_page + 1, 1)
    page = max(min(page, pages), 1)
    start = (page - 1) * per_page
    end = start + per_page
    items = user_lands[start:end]

    def page_url(p):
        args = request.args.to_dict()
        args['page'] = p
        return url_for('main.my_lands', **args)

    pagination = {
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'total': total,
        'has_prev': page > 1,
        'has_next': page < pages
    }

    return render_template('my_lands.html',
                           lands=items,
                           pagination=pagination,
                           page_url=page_url,
                           CATEGORY_MAP=CATEGORY_MAP)

# ---------------- پروفایل ----------------
@main_bp.route('/profile')
def profile():
    if 'user_phone' not in session:
        flash("برای مشاهده پروفایل وارد شوید.")
        session['next'] = url_for('main.profile')
        return redirect(url_for('main.send_otp'))

    users = load_users()
    user = next((u for u in users if u.get('phone') == session['user_phone']), None)
    return render_template('profile.html', user=user)

# ---------------- علاقه‌مندی‌ها (کلاینت‌ساید) ----------------
@main_bp.route('/favorites')
def favorites():
    return render_template('favorites.html')

# ---------------- ویرایش آگهی ----------------
@main_bp.route('/lands/edit/<code>', methods=['GET', 'POST'])
def edit_land(code):
    if 'user_phone' not in session:
        flash("برای ویرایش آگهی وارد شوید.")
        session['next'] = url_for('main.edit_land', code=code)
        return redirect(url_for('main.send_otp'))

    lands = load_ads()
    land = next((l for l in lands if l.get('code') == code and l.get('owner') == session['user_phone']), None)
    if not land:
        flash("آگهی پیدا نشد.")
        return redirect(url_for('main.my_lands'))

    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        if category and category not in CATEGORY_KEYS:
            category = land.get('category', '')

        land.update({
            'title': request.form.get('title'),
            'location': request.form.get('location'),
            'size': request.form.get('size'),
            'price_total': _to_int(request.form.get('price_total')) if request.form.get('price_total') else None,
            'description': request.form.get('description'),
            'category': category
        })

        images = request.files.getlist('images')
        folder = os.path.join(_data_dir(), 'uploads')
        os.makedirs(folder, exist_ok=True)
        saved = []
        for img in images:
            if img and img.filename:
                fname = f"{code}__{secure_filename(img.filename)}"
                path = os.path.join(folder, fname)
                img.save(path)
                saved.append(fname)
        if saved:
            land['images'] = saved

        save_ads(lands)
        flash("✅ آگهی با موفقیت ویرایش شد.")
        return redirect(url_for('main.my_lands'))

    return render_template('edit_land.html', land=land, CATEGORY_MAP=CATEGORY_MAP)

# ---------------- حذف آگهی ----------------
@main_bp.route('/lands/delete/<code>', methods=['POST'])
def delete_land(code):
    if 'user_phone' not in session:
        flash("برای حذف آگهی وارد شوید.")
        return redirect(url_for('main.send_otp'))

    lands = load_ads()
    new_lands = [l for l in lands if not (l.get('code') == code and l.get('owner') == session['user_phone'])]

    if len(new_lands) == len(lands):
        flash("❌ آگهی پیدا نشد یا متعلق به شما نیست.")
    else:
        save_ads(new_lands)
        flash("🗑️ آگهی حذف شد.")

    return redirect(url_for('main.my_lands'))

# ---------------- تنظیمات کاربری ----------------
@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_phone' not in session:
        flash("برای ورود به تنظیمات وارد شوید.")
        session['next'] = url_for('main.settings')
        return redirect(url_for('main.send_otp'))

    users = load_users()
    phone = session['user_phone']
    user = next((u for u in users if u.get('phone') == phone), None)

    if not user:
        flash("کاربر یافت نشد.")
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        user['name'] = request.form.get('name', '').strip()
        user['lastname'] = request.form.get('lastname', '').strip()
        user['province'] = request.form.get('province', '').strip()
        user['city'] = request.form.get('city', '').strip()
        new_password = request.form.get('password', '').strip()
        if new_password:
            user['password'] = new_password

        save_users(users)
        flash("✅ تنظیمات با موفقیت ذخیره شد.")
        return redirect(url_for('main.settings'))

    return render_template('settings.html', user=user)

# ---------------- صفحه فهرست با فیلتر دسته ----------------
@main_bp.route('/search')
def search_page():
    active_category = request.args.get('category', '').strip()
    if active_category and active_category not in CATEGORY_KEYS:
        active_category = ""

    ads = [ad for ad in load_ads() if ad.get('status') == 'approved']

    if active_category:
        ads = [ad for ad in ads if ad.get('category', '') == active_category]

    ads = sorted(ads, key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)
    return render_template('search.html', ads=ads, category=active_category, CATEGORY_MAP=CATEGORY_MAP)

# ---------------- نتایج جست‌وجوی متنی ----------------
@main_bp.route('/search-results')
def search_results():
    query = (request.args.get('q', '') or '').strip()
    q = query.lower()

    all_ads = load_ads()
    pool = [ad for ad in all_ads if ad.get('status') == 'approved']

    results = []
    for ad in pool:
        title = (ad.get('title') or '').lower()
        loc = (ad.get('location') or '').lower()
        desc = (ad.get('description') or '').lower()
        if q and (q in title or q in loc or q in desc):
            results.append(ad)

    results = sorted(results, key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)
    return render_template('search_results.html', results=results, query=query, CATEGORY_MAP=CATEGORY_MAP)

# ---------- اعلان‌ها (Notifications) ----------
def _notifications_file(app=None):
    return _ensure_file('NOTIFICATIONS_FILE', 'notifications.json', [], app)

def load_notifications(app=None):
    return load_json(_notifications_file(app))

def save_notifications(items, app=None):
    save_json(_notifications_file(app), items)

def user_unread_notifications_count(phone):
    if not phone:
        return 0
    items = load_notifications()
    return sum(1 for n in items if n.get('to') == phone and not n.get('read'))

@main_bp.app_context_processor
def inject_notifications_count():
    phone = session.get('user_phone')
    return {'notif_count': user_unread_notifications_count(phone)}

@main_bp.route('/notifications')
def notifications():
    phone = session.get('user_phone')
    if not phone:
        flash('برای دیدن اعلان‌ها ابتدا وارد شوید.', 'warning')
        return redirect(url_for('main.send_otp'))

    items = load_notifications()
    my_items = [n for n in items if n.get('to') == phone]

    def sort_key(n):
        return n.get('created_at') or n.get('id') or 0
    my_items.sort(key=sort_key, reverse=True)

    return render_template('notifications.html', items=my_items)

@main_bp.route('/notifications/read-all', methods=['POST'])
def notifications_read_all():
    phone = session.get('user_phone')
    if not phone:
        flash('ابتدا وارد شوید.', 'warning')
        return redirect(url_for('main.send_otp'))

    items = load_notifications()
    changed = False
    for n in items:
        if n.get('to') == phone and not n.get('read'):
            n['read'] = True
            changed = True
    if changed:
        save_notifications(items)
    flash('همه اعلان‌ها خوانده شد.', 'success')
    return redirect(url_for('main.notifications'))

# ---------------- انتخاب شهر ----------------
@main_bp.route('/city')
def city_select():
    return render_template('city_select.html')

# ---------------- روت‌های عیب‌یابی ----------------
@main_bp.route('/healthz')
def healthz():
    try:
        _ = load_ads()
        return "ok", 200
    except Exception as e:
        try:
            current_app.logger.exception("Health error: %s", e)
        except Exception:
            pass
        return "not ok", 500

@main_bp.route('/diag')
def diag():
    info = {}
    try:
        app = current_app
        info['instance_path'] = app.instance_path
        data_dir = _data_dir()
        info['data_dir'] = data_dir
        info['writable'] = os.access(data_dir, os.W_OK)
        test_file = os.path.join(data_dir, '.__write_test')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
        os.remove(test_file)
        info['write_test'] = 'ok'
    except Exception as e:
        info['write_test'] = f'error: {e}'
    return info, 200

# ---------------- هندلر خطای عمومی (اختیاری) ----------------
@main_bp.app_errorhandler(Exception)
def handle_any_error(e):
    try:
        current_app.logger.exception("Unhandled error: %s", e)
    except Exception:
        pass
    try:
        return render_template('500.html'), 500
    except Exception:
        return "Internal Server Error", 500
