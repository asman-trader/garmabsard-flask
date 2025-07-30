import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'your_secret_key_here'  # کلید امنیتی برای سشن‌ها

    # ✅ مسیر جدید پوشه آپلود داخل فولدر data
    UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, '..', 'data', 'uploads'))

    # ✅ مسیر فایل‌های JSON داده
    LANDS_FILE = os.path.abspath(os.path.join(BASE_DIR, 'data', 'lands.json'))
    CONSULTS_FILE = os.path.abspath(os.path.join(BASE_DIR, 'data', 'consults.json'))
    USERS_FILE = os.path.abspath(os.path.join(BASE_DIR, 'data', 'users.json'))
    SETTINGS_FILE = os.path.abspath(os.path.join(BASE_DIR, 'data', 'settings.json'))




