# passenger_wsgi.py (یا wsgi.py)
import sys, os, traceback, json

# 1) مسیر پروژه و sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # دایرکتوری کاری جهت ایمپورت‌های نسبی

# 2) اتصال به venv
# توصیه‌شده: در .htaccess این را ست کن و این بخش را نادیده بگیر:
#   PassengerPython /home/<USER>/virtualenv/myapp/3.11/bin/python
VENV_ACTIVATE = '/home/garmabs2/virtualenv/myapp/3.11/bin/activate_this.py'
if os.path.exists(VENV_ACTIVATE):
    with open(VENV_ACTIVATE) as f:
        exec(f.read(), {'__file__': VENV_ACTIVATE})

# 3) ساخت مسیر instance و لاگ
INSTANCE_PATH = os.environ.get('INSTANCE_PATH', os.path.join(PROJECT_ROOT, 'instance'))
os.makedirs(INSTANCE_PATH, exist_ok=True)
# تلاش برای بارگذاری کلیدهای VAPID از فایل پایدار در instance/data/vapid.json
try:
    data_dir = os.path.join(INSTANCE_PATH, 'data')
    os.makedirs(data_dir, exist_ok=True)
    vapid_file = os.path.join(data_dir, 'vapid.json')
    if os.path.exists(vapid_file):
        with open(vapid_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f) or {}
        pub = (cfg.get('VAPID_PUBLIC_KEY') or '').strip()
        prv = (cfg.get('VAPID_PRIVATE_KEY') or '').strip()
        sub = (cfg.get('VAPID_SUB') or '').strip()
        if pub and not os.environ.get('VAPID_PUBLIC_KEY'):
            os.environ['VAPID_PUBLIC_KEY'] = pub
        if prv and not os.environ.get('VAPID_PRIVATE_KEY'):
            os.environ['VAPID_PRIVATE_KEY'] = prv
        if sub and not os.environ.get('VAPID_SUB'):
            os.environ['VAPID_SUB'] = sub
except Exception:
    pass
LOG_DIR = os.path.join(INSTANCE_PATH, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'wsgi.log')

def _log(msg: str):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as fh:
            fh.write(msg + '\n')
    except Exception:
        pass

# 4) بارگذاری اپ
try:
    from app import create_app  # باید در ریشه پروژه، پکیج/ماژول app با create_app داشته باشی
    application = create_app()
    _log('WSGI loaded OK')
except Exception:
    _log('WSGI load error:\n' + traceback.format_exc())

    # پاسخ خوانا به کاربر و ارجاع به لاگ
    def application(environ, start_response):
        status = '500 INTERNAL SERVER ERROR'
        out = b'Application failed to start; check instance/logs/wsgi.log'
        start_response(status, [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(out))),
        ])
        return [out]
