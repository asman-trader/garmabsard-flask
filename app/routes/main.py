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
    "titled": "سنددار",
    "with_utilities": "دارای آب و برق",
    "good_price": "قیمت مناسب"
}
CATEGORY_KEYS = set(CATEGORY_MAP.keys()) - {""}

# ---------------- ابزارهای کمکی ----------------
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

def get_land_by_code(code):
    lands = load_json(current_app.config['LANDS_FILE'])
    return next((l for l in lands if l.get('code') == code), None)

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

def parse_datetime_safe(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except Exception:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return datetime(1970, 1, 1)

def load_ads():
    return load_json(current_app.config['LANDS_FILE'])

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
    sorted_lands = sorted(approved, key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)
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
    consults = load_json(current_app.config['CONSULTS_FILE'])
    consults.append({
        'name': request.form.get('name'),
        'phone': request.form.get('phone'),
        'message': request.form.get('message'),
        'code': code,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_json(current_app.config['CONSULTS_FILE'], consults)
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
        users = load_json(current_app.config['USERS_FILE'])
        if not any(u.get('phone') == phone for u in users):
            users.append({'phone': phone, 'registered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            save_json(current_app.config['USERS_FILE'], users)
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
            # اگر مقدار نادرست آمد، نادیده بگیر
            category = ""

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
                'price_total': int(price_total) if price_total else None,
                'description': description,
                'category': category  # ممکن است خالی باشد
            },
            'land_images': image_names
        })
        return redirect(url_for('main.add_land_step3'))

    # برای فرم: CATEGORY_MAP را بده تا در Select استفاده شود
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

    approval_method = 'manual'
    settings_file = current_app.config['SETTINGS_FILE']
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                approval_method = json.load(f).get('approval_method', 'manual')
        except Exception:
            pass

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
        'category': lt.get('category', '')  # ممکن است خالی باشد
    }

    lands.append(new_land)
    save_json(current_app.config['LANDS_FILE'], lands)

    for k in keys:
        session.pop(k, None)

    msg = "✅ آگهی شما با موفقیت ثبت شد." + (" به صورت خودکار منتشر شد." if status == 'approved' else " و در انتظار تأیید قرار گرفت.")
    flash(msg)
    return redirect(url_for('main.my_lands'))

# ---------------- آگهی‌های من ----------------
@main_bp.route('/my-lands')
def my_lands():
    if 'user_phone' not in session:
        flash("برای مشاهده آگهی‌ها وارد شوید.")
        session['next'] = url_for('main.my_lands')
        return redirect(url_for('main.send_otp'))

    lands = load_ads()
    user_lands = [l for l in lands if l.get('owner') == session['user_phone']]
    # نمایش همه وضعیت‌ها برای صاحب آگهی
    return render_template('my_lands.html', lands=user_lands, CATEGORY_MAP=CATEGORY_MAP)

# ---------------- پروفایل ----------------
@main_bp.route('/profile')
def profile():
    if 'user_phone' not in session:
        flash("برای مشاهده پروفایل وارد شوید.")
        session['next'] = url_for('main.profile')
        return redirect(url_for('main.send_otp'))

    users = load_json(current_app.config['USERS_FILE'])
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
            'price_total': int(request.form.get('price_total')) if request.form.get('price_total') else None,
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

        save_json(current_app.config['LANDS_FILE'], lands)
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
        save_json(current_app.config['LANDS_FILE'], new_lands)
        flash("🗑️ آگهی حذف شد.")

    return redirect(url_for('main.my_lands'))

# ---------------- تنظیمات کاربری ----------------
@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_phone' not in session:
        flash("برای ورود به تنظیمات وارد شوید.")
        session['next'] = url_for('main.settings')
        return redirect(url_for('main.send_otp'))

    users = load_json(current_app.config['USERS_FILE'])
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

        save_json(current_app.config['USERS_FILE'], users)
        flash("✅ تنظیمات با موفقیت ذخیره شد.")
        return redirect(url_for('main.settings'))

    return render_template('settings.html', user=user)

# ---------------- صفحه فهرست با فیلتر دسته ----------------
@main_bp.route('/search')
def search_page():
    # دسته‌ی فعال از URL
    active_category = request.args.get('category', '').strip()
    if active_category and active_category not in CATEGORY_KEYS:
        # اگر کلید نامعتبر بود، آن را خالی کن تا «همه» شود
        active_category = ""

    # همه آگهی‌های تایید شده
    ads = [ad for ad in load_ads() if ad.get('status') == 'approved']

    # فیلتر بر اساس دسته (در صورت وجود)
    if active_category:
        ads = [ad for ad in ads if ad.get('category', '') == active_category]

    # مرتب‌سازی جدیدترین اول
    ads = sorted(ads, key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)

    # می‌توانی پارامترهای دیگری مثل sort/page را هم در قالب هندل کنی
    return render_template('search.html', ads=ads, category=active_category, CATEGORY_MAP=CATEGORY_MAP)

# ---------------- نتایج جست‌وجوی متنی ----------------
@main_bp.route('/search-results')
def search_results():
    query = (request.args.get('q', '') or '').strip()
    q = query.lower()

    all_ads = load_ads()
    # فقط تاییدشده‌ها
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
from flask import flash

def _notifications_file():
    # اگر جایی ست‌ نکردی، به صورت پیش‌فرض فایل را در app/data/notifications.json می‌سازیم
    default_path = os.path.join(current_app.root_path, 'data', 'notifications.json')
    current_app.config.setdefault('NOTIFICATIONS_FILE', default_path)
    # اگر پوشه data وجود نداشت، بساز
    os.makedirs(os.path.dirname(current_app.config['NOTIFICATIONS_FILE']), exist_ok=True)
    # اگر فایل وجود ندارد، یک آرایه خالی ذخیره کن
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
    # این متغیر در همه قالب‌ها در دسترس است: notif_count
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
    # مرتب‌سازی نزولی بر اساس زمان ایجاد (created_at) اگر باشد، وگرنه بر اساس id/آخر لیست
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

