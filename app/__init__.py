import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.routes.main import main_bp
from app.routes.admin import admin_bp
from app.models import db

def create_app():
    app = Flask(__name__)
    app.secret_key = 'my-secret-key'

    # تنظیمات پایگاه‌داده SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # تنظیم مسیر فایل‌ها
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    app.config['LANDS_FILE'] = os.path.join('data', 'lands.json')
    app.config['CONSULTS_FILE'] = os.path.join('data', 'consults.json')
    app.config['USERS_FILE'] = os.path.join('data', 'users.json')
    app.config['SETTINGS_FILE'] = os.path.join('data', 'settings.json')

    # ساخت مسیرهای موردنیاز در صورت نبود
    os.makedirs('data', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ایجاد فایل‌های JSON اولیه
    for filename in ['lands.json', 'consults.json', 'users.json', 'settings.json']:
        filepath = os.path.join('data', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('[]')

    # مقداردهی اولیه دیتابیس
    db.init_app(app)

    # ثبت بلوپرینت‌ها
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
