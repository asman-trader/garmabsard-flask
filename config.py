# app/config.py
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # .../app

def _abs(*parts: str) -> str:
    return os.path.abspath(os.path.join(*parts))

class Config:
    # --- امنیت و سشن ---
    SECRET_KEY = "vinor-dev-keep-it-constant-and-change-in-prod"  # در پروداکشن از متغیر محیطی بگیر
    SESSION_COOKIE_NAME = "vinor_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False         # چون روی HTTP محلی هستی؛ روی سرور HTTPS حتما True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=6)

    # --- CSRF (اگر Flask-WTF داری) ---
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600            # 1 ساعت
    # اگر از CSRFProtect بدون Flask-WTF استفاده می‌کنی، در تمپلیت <input name="csrf_token" ...> را خودت بگذار

    # --- دیباگ/رندر ---
    TEMPLATES_AUTO_RELOAD = True          # برای توسعه راحت‌تر
    JSON_AS_ASCII = False

    # --- مسیرهای داده و آپلود (یکدست داخل app/data) ---
    DATA_DIR = _abs(BASE_DIR, "data")
    UPLOAD_FOLDER = _abs(DATA_DIR, "uploads")        # app/data/uploads
    LANDS_FILE   = _abs(DATA_DIR, "lands.json")
    CONSULTS_FILE= _abs(DATA_DIR, "consults.json")
    USERS_FILE   = _abs(DATA_DIR, "users.json")
    SETTINGS_FILE= _abs(DATA_DIR, "settings.json")

    # --- محدودیت آپلود ---
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True          # روی HTTPS
    # SECRET_KEY = os.environ.get("SECRET_KEY")  # حتماً از محیط بگیر

# helper: در app factory بعد از ساخت app، با این اسنیپت پوشه‌ها را مطمئن بساز:
# os.makedirs(app.config["DATA_DIR"], exist_ok=True)
# os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
