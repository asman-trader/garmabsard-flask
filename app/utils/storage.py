# app/utils/storage.py
import os, json, shutil
from flask import current_app

# -------- مسیرهای داده --------
def data_dir(app=None):
    """
    مسیر امن و قابل‌نوشتن: <instance>/data  (داخل instance_path)
    """
    app = app or current_app
    base = app.instance_path
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, 'data')
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, 'uploads'), exist_ok=True)
    return path

def legacy_dir(app=None):
    """مسیر قدیمی کنار کد: <root>/data"""
    app = app or current_app
    return os.path.join(app.root_path, 'data')

# -------- اطمینان از وجود فایل و مهاجرت --------
def ensure_file(config_key: str, filename: str, default_content, app=None):
    """
    اگر فایل کانفیگ‌شده وجود نداشته باشد:
      1) تلاش برای کپی از مسیر قدیمی (root/data)
      2) در غیر این صورت ایجاد فایل با محتوای پیش‌فرض
    همچنین مسیر به app.config[config_key] ست می‌شود.
    """
    app = app or current_app
    d = data_dir(app)
    fpath = app.config.get(config_key) or os.path.join(d, filename)
    app.config[config_key] = fpath

    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    if not os.path.exists(fpath):
        old = os.path.join(legacy_dir(app), filename)
        if os.path.exists(old):
            try:
                shutil.copy2(old, fpath)
            except Exception:
                pass
        if not os.path.exists(fpath):
            with open(fpath, 'w', encoding='utf-8') as f:
                if isinstance(default_content, (dict, list)):
                    json.dump(default_content, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(default_content or ""))
    return fpath

def migrate_legacy(app=None):
    """
    کپی فایل‌های قدیمی از <root>/data به <instance>/data در اولین اجرا
    """
    app = app or current_app
    inst = data_dir(app)
    legacy = legacy_dir(app)
    try:
        for name in ('lands.json','users.json','consults.json','settings.json','notifications.json','reports.json'):
            old, new = os.path.join(legacy, name), os.path.join(inst, name)
            if os.path.exists(old) and not os.path.exists(new):
                try: shutil.copy2(old, new)
                except Exception: pass

        old_up, new_up = os.path.join(legacy, 'uploads'), os.path.join(inst, 'uploads')
        if os.path.isdir(old_up):
            if not os.path.exists(new_up) or (os.path.exists(new_up) and not os.listdir(new_up)):
                try: shutil.copytree(old_up, new_up, dirs_exist_ok=True)
                except Exception: pass
    except Exception as e:
        try: app.logger.warning("Legacy migration issue: %s", e)
        except Exception: pass

# -------- IO ساده JSON --------
def _load(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:    return json.load(f)
            except: return []
    return []

def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# فایل‌های دامنه
_ADS_CACHE = {"path": None, "mtime": None, "size": None, "data": None}

def load_ads(app=None):        return _load(ensure_file('LANDS_FILE','lands.json',[],app))

def load_ads_cached(app=None):
    """لود آگهی‌ها با کش ساده مبتنی بر mtime/size فایل."""
    app = app or current_app
    path = ensure_file('LANDS_FILE','lands.json',[],app)
    try:
        st = os.stat(path)
        mtime = st.st_mtime_ns if hasattr(st, 'st_mtime_ns') else int(st.st_mtime * 1e9)
        size = st.st_size
    except Exception:
        mtime = None
        size = None

    c = _ADS_CACHE
    if c["path"] == path and c["mtime"] == mtime and c["size"] == size and c["data"] is not None:
        return c["data"]

    data = _load(path)
    _ADS_CACHE.update({"path": path, "mtime": mtime, "size": size, "data": data})
    return data

def _update_ads_cache_after_save(path, items):
    try:
        st = os.stat(path)
        mtime = st.st_mtime_ns if hasattr(st, 'st_mtime_ns') else int(st.st_mtime * 1e9)
        size = st.st_size
    except Exception:
        mtime = None
        size = None
    _ADS_CACHE.update({"path": path, "mtime": mtime, "size": size, "data": items})

def save_ads(items, app=None):
    path = ensure_file('LANDS_FILE','lands.json',[],app)
    _save(path, items)
    _update_ads_cache_after_save(path, items)

def load_users(app=None):        return _load(ensure_file('USERS_FILE','users.json',[],app))
def save_users(items, app=None): return _save(ensure_file('USERS_FILE','users.json',[],app), items)

def load_consults(app=None):        return _load(ensure_file('CONSULTS_FILE','consults.json',[],app))
def save_consults(items, app=None): return _save(ensure_file('CONSULTS_FILE','consults.json',[],app), items)

def load_settings(app=None):  
    default_settings = {
        "approval_method": "manual",
        "show_submit_button": True,
        "ad_expiry_days": 30,
        "sms_line_number": "300089930616",
        "partner_application_sms_message": "درخواست همکاری شما ثبت شد و در حال بررسی است. وینور",
        "partner_approval_sms_message": "پنل همکاری وینور برای شما فعال شد. وینور",
        "partner_application_admin_phone": "09121471301",
        "partner_application_admin_sms_message": "درخواست همکاری جدید همکار در وینور ثبت شد.",
    }
    return _load(ensure_file('SETTINGS_FILE','settings.json',default_settings,app))

# شهرهای فعال برای همکاری
def load_active_cities(app=None):        return _load(ensure_file('ACTIVE_CITIES_FILE','active_cities.json',["تهران", "کرج", "اصفهان", "شیراز", "مشهد", "تبریز"],app))
def save_active_cities(items, app=None): return _save(ensure_file('ACTIVE_CITIES_FILE','active_cities.json',[],app), items)

def load_notifications(app=None):        return _load(ensure_file('NOTIFICATIONS_FILE','notifications.json',[],app))
def save_notifications(items, app=None): return _save(ensure_file('NOTIFICATIONS_FILE','notifications.json',[],app), items)

# Reports (user-reported ads)
def load_reports(app=None):        return _load(ensure_file('REPORTS_FILE','reports.json',[],app))
def save_reports(items, app=None): return _save(ensure_file('REPORTS_FILE','reports.json',[],app), items)

# Consultants & Applications
def load_consultant_apps(app=None):        return _load(ensure_file('CONSULTANT_APPS_FILE','consultant_applications.json',[],app))
def save_consultant_apps(items, app=None): return _save(ensure_file('CONSULTANT_APPS_FILE','consultant_applications.json',[],app), items)
def load_consultants(app=None):           return _load(ensure_file('CONSULTANTS_FILE','consultants.json',[],app))
def save_consultants(items, app=None):    return _save(ensure_file('CONSULTANTS_FILE','consultants.json',[],app), items)

# Express Partners & Applications
def load_express_partner_apps(app=None):   return _load(ensure_file('EXPRESS_PARTNER_APPS_FILE','express_partner_applications.json',[],app))
def save_express_partner_apps(items, app=None): return _save(ensure_file('EXPRESS_PARTNER_APPS_FILE','express_partner_applications.json',[],app), items)
def load_express_partners(app=None):       return _load(ensure_file('EXPRESS_PARTNERS_FILE','express_partners.json',[],app))
def save_express_partners(items, app=None): return _save(ensure_file('EXPRESS_PARTNERS_FILE','express_partners.json',[],app), items)

# Express Partner: Notes, Sales, Files (metadata)
def load_partner_notes(app=None):          return _load(ensure_file('EXPRESS_PARTNER_NOTES_FILE','express_partner_notes.json',[],app))
def save_partner_notes(items, app=None):   return _save(ensure_file('EXPRESS_PARTNER_NOTES_FILE','express_partner_notes.json',[],app), items)
def load_partner_sales(app=None):          return _load(ensure_file('EXPRESS_PARTNER_SALES_FILE','express_partner_sales.json',[],app))
def save_partner_sales(items, app=None):   return _save(ensure_file('EXPRESS_PARTNER_SALES_FILE','express_partner_sales.json',[],app), items)
def load_partner_files_meta(app=None):     return _load(ensure_file('EXPRESS_PARTNER_FILES_META_FILE','express_partner_files.json',[],app))
def save_partner_files_meta(items, app=None): return _save(ensure_file('EXPRESS_PARTNER_FILES_META_FILE','express_partner_files.json',[],app), items)

# Express Assignments & Commissions
def load_express_assignments(app=None):    return _load(ensure_file('EXPRESS_ASSIGNMENTS_FILE','express_assignments.json',[],app))
def save_express_assignments(items, app=None): return _save(ensure_file('EXPRESS_ASSIGNMENTS_FILE','express_assignments.json',[],app), items)
def load_express_commissions(app=None):    return _load(ensure_file('EXPRESS_COMMISSIONS_FILE','express_commissions.json',[],app))
def save_express_commissions(items, app=None): return _save(ensure_file('EXPRESS_COMMISSIONS_FILE','express_commissions.json',[],app), items)

# SMS History
def load_sms_history(app=None):    return _load(ensure_file('SMS_HISTORY_FILE','sms_history.json',[],app))
def save_sms_history(items, app=None): return _save(ensure_file('SMS_HISTORY_FILE','sms_history.json',[],app), items)