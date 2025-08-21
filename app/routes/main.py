from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
import os, json, random, requests, subprocess
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
    "titled": "सنددار",
    "with_utilities": "دارای آب و برق",
    "good_price": "قیمت مناسب"
}
CATEGORY_KEYS = set(CATEGORY_MAP.keys()) - {""}

# ---------------- ابزارهای کمکی مسیر/فایل ----------------
def _data_dir():
    path = os.path.join(current_app.root_path, 'data')
    os.makedirs(path, exist_ok=True)
    return path

def _ensure_file(config_key: str, filename: str, default_content):
    """
    اگر config_key ست نشده باشد یا فایل وجود نداشته باشد:
      - مسیر پیش‌فرض data/<filename> ساخته می‌شود
      - فایل با default_content ایجاد می‌شود
    در نهایت مسیر را در config ثبت و برمی‌گرداند.
    """
    # اگر مسیر از قبل ست شده:
    fpath = current_app.config.get(config_key)
    if not fpath:
        fpath = os.path.join(_data_dir(), filename)
        current_app.config[config_key] = fpath

    os.makedirs(os.path.dirname(fpath), exist_ok=True)
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
        # حذف کاما و فاصله برای اطمینان
        return int(str(x).replace(',', '').strip())
    except Exception:
        return default

def load_ads():
    path = _ensure_file('LANDS_FILE', 'lands.json', [])
    return load_json(path)

def save_ads(items):
    path = _ensure_file('LANDS_FILE', 'lands.json', [])
    save_json(path, items)

def load_users():
    path = _ensure_file('USERS_FILE', 'users.json', [])
    return load_json(path)

def save_users(items):
    path = _ensure_file('USERS_FILE', 'users.json', [])
    save_json(path, items)

def load_consults():
    path = _ensure_file('CONSULTS_FILE', 'consults.json', [])
    return load_json(path)

def save_consults(items):
    path = _ensure_file('CONSULTS_FILE', 'consults.json', [])
    save_json(path, items)

def load_settings():
    path = _ensure_file('SETTINGS_FILE', 'settings.json', {"approval_method": "manual"})
    return load_json(path)

def get_land_by_code(code):
    lands = load_ads()
    return next((l for l in lands if l.get('code') == code), None)

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
    folder = os.path.join(current_app.root_path, 'data', 'uploads')
    return send_from_directory(folder, filename)

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
            category = ""  # مقدار نامعتبر را نادیده بگیر

        images = request.files.getlist('images')

        if not title or not location or not size:
            flash("همه فیلدها الزامی هستند.")
            return redirect(url_for('main.add_land'))

        code = datetime.now().strftime('%Y%m%d%H%M%S')
        upload_dir = os.path.join(current_app.root_path, 'data', 'uploads')
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

    # پارامترها
    q        = (request.args.get('q') or '').strip().lower()
    status   = (request.args.get('status') or '').strip()
    sort     = (request.args.get('sort') or 'new').strip()
    page     = int(request.args.get('page', 1) or 1)
    per_page = min(int(request.args.get('per_page', 12) or 12), 48)

    # داده خام
    lands_all = load_ads()
    user_lands = [l for l in lands_all if l.get('owner') == session['user_phone']]

    # فیلتر وضعیت
    if status in {'approved', 'pending', 'rejected'}:
        user_lands = [l for l in user_lands if l.get('status') == status]

    # جستجو (عنوان/لوکیشن/توضیح/کد)
    if q:
        def _hit(ad):
            title = (ad.get('title') or '').lower()
            loc   = (ad.get('location') or '').lower()
            desc  = (ad.get('description') or '').lower()
            code  = str(ad.get('code') or '')
            return (q in title) or (q in loc) or (q in desc) or (q == code)
        user_lands = [ad for ad in user_lands if _hit(ad)]

    # مرتب‌سازی
    if sort == 'old':
        user_lands.sort(key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')))
    elif sort == 'size_desc':
        user_lands.sort(key=lambda x: _to_int(x.get('size')), reverse=True)
    elif sort == 'size_asc':
        user_lands.sort(key=lambda x: _to_int(x.get('size')))
    else:  # new
        user_lands.sort(key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)

    # صفحه‌بندی ساده
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
        folder = os.path.join(current_app.root_path, 'data', 'uploads')
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
def _notifications_file():
    default_path = os.path.join(current_app.root_path, 'data', 'notifications.json')
    current_app.config.setdefault('NOTIFICATIONS_FILE', default_path)
    os.makedirs(os.path.dirname(current_app.config['NOTIFICATIONS_FILE']), exist_ok=True)
    if not os.path.exists(current_app.config['NOTIFICATIONS_FILE']):
        save_json(current_app.config['NOTIFICATIONS_FILE'], [])
    return current_app.config['NOTIFICATIONS_FILE']

def load_notifications():
    return load_json(_notifications_file())

def save_notifications(items):
    save_json(_notifications_file(), items)

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
