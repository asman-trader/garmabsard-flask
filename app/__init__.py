import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.routes.main import main_bp
from app.routes.admin import admin_bp
from app.models import db

def create_app():
    app = Flask(__name__)
    app.secret_key = 'my-secret-key'

    # تنظیمات پایگاه داده SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # مسیرهای مربوط به فایل‌ها و آپلودها
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    app.config['LANDS_FILE'] = os.path.join('data', 'lands.json')
    app.config['CONSULTS_FILE'] = os.path.join('data', 'consults.json')
    app.config['USERS_FILE'] = os.path.join('data', 'users.json')
    app.config['SETTINGS_FILE'] = os.path.join('data', 'settings.json')  # ✅ اضافه‌شده برای رفع خطا

    # اطمینان از وجود مسیرهای لازم
    os.makedirs('data', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ایجاد فایل‌های JSON در اولین اجرا
    for json_file in ['lands.json', 'consults.json', 'users.json', 'settings.json']:
        path = os.path.join('data', json_file)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write('[]')

    # اتصال به دیتابیس
    db.init_app(app)

    # ثبت بلوپرینت‌ها
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
