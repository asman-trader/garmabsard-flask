# passenger_wsgi.py — Phusion Passenger (Flask)
import json
import os
import sys
import traceback

# مسیر ریشه پروژه
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# اضافه کردن مسیر پروژه به پایتون
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# تنظیم دایرکتوری کاری
os.chdir(PROJECT_ROOT)

# اختیاری: فعال‌سازی virtualenv اگر مسیر activate_this.py را در env گذاشتی
# (یا در .htaccess با PassengerPython به باینری venv اشاره کن.)
_activate = os.environ.get("PASSENGER_ACTIVATE_THIS", "").strip()
if _activate and os.path.isfile(_activate):
    with open(_activate, encoding="utf-8") as _f:
        exec(_f.read(), {"__file__": _activate})

# ساخت پوشه instance اگر نبود
INSTANCE_PATH = os.path.join(PROJECT_ROOT, "instance")
os.makedirs(INSTANCE_PATH, exist_ok=True)

# پوشه لاگ
LOG_DIR = os.path.join(INSTANCE_PATH, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "wsgi.log")


def log(message: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


# کلیدهای VAPID از instance/data/vapid.json (اختیاری)
try:
    _data_dir = os.path.join(INSTANCE_PATH, "data")
    os.makedirs(_data_dir, exist_ok=True)
    _vapid_file = os.path.join(_data_dir, "vapid.json")
    if os.path.isfile(_vapid_file):
        with open(_vapid_file, encoding="utf-8") as f:
            cfg = json.load(f) or {}
        pub = (cfg.get("VAPID_PUBLIC_KEY") or "").strip()
        prv = (cfg.get("VAPID_PRIVATE_KEY") or "").strip()
        sub = (cfg.get("VAPID_SUB") or "").strip()
        if pub and not os.environ.get("VAPID_PUBLIC_KEY"):
            os.environ["VAPID_PUBLIC_KEY"] = pub
        if prv and not os.environ.get("VAPID_PRIVATE_KEY"):
            os.environ["VAPID_PRIVATE_KEY"] = prv
        if sub and not os.environ.get("VAPID_SUB"):
            os.environ["VAPID_SUB"] = sub
except Exception:
    pass


try:
    from app import create_app

    application = create_app()
    log("WSGI loaded successfully")
except Exception:
    log("WSGI load error:\n" + traceback.format_exc())

    def application(environ, start_response):
        status = "500 INTERNAL SERVER ERROR"
        body = b"Application failed to start. Check instance/logs/wsgi.log"
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
        start_response(status, headers)
        return [body]
