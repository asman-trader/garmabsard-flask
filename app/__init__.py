import os
from flask import Flask

def create_app():
    # اپ با مسیر instance (برای هاست‌ها writeable است)
    app = Flask(__name__, instance_relative_config=True)

    # کلید سشن — در پروداکشن حتماً از ENV ست کن
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-please-32bytes')
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # ---- ساخت مسیرهای ضروری در instance/ ----
    inst = app.instance_path                              # <project>/instance
    data_dir = os.path.join(inst, 'data')                 # <project>/instance/data
    uploads_dir = os.path.join(data_dir, 'uploads')       # <project>/instance/data/uploads
    logs_dir = os.path.join(inst, 'logs')                 # <project>/instance/logs
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # ---- پایگاه‌داده (SQLite) در instance/data ----
    db_path = os.path.join(data_dir, 'database.db')
    # sqlite URI باید اسلش-فوروارد داشته باشد
    db_uri = 'sqlite:///' + db_path.replace('\\', '/')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', db_uri)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ---- مسیر/نام فایل‌های JSON (همگی در instance/data) ----
    app.config.setdefault('UPLOAD_FOLDER', uploads_dir)
    app.config.setdefault('LANDS_FILE',      os.path.join(data_dir, 'lands.json'))
    app.config.setdefault('CONSULTS_FILE',   os.path.join(data_dir, 'consults.json'))
    app.config.setdefault('USERS_FILE',      os.path.join(data_dir, 'users.json'))
    app.config.setdefault('SETTINGS_FILE',   os.path.join(data_dir, 'settings.json'))
    app.config.setdefault('NOTIFICATIONS_FILE', os.path.join(data_dir, 'notifications.json'))

    # ---- مقداردهی SQLAlchemy ----
    # توجه: import داخل تابع تا از چرخه‌ی ایمپورت جلوگیری شود
    from app.models import db
    db.init_app(app)
    # (اختیاری) ساخت جدول‌ها در صورت نبود
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            # اگر مدل/پایگاه‌داده ندارید یا فعلاً لازم نیست، می‌توان نادیده گرفت
            pass

    # ---- ثبت بلوپرینت‌ها (ایمپورت داخل تابع) ----
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.webhook import webhook_bp

    app.register_blueprint(main_bp)                 # /
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(webhook_bp)              # /git-webhook

    # ---- لاگ فایل چرخشی در instance/logs/app.log (اختیاری ولی مفید) ----
    try:
        import logging
        from logging.handlers import RotatingFileHandler
        app_log_file = os.path.join(logs_dir, 'app.log')
        if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
            fh = RotatingFileHandler(app_log_file, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
            fh.setLevel(logging.INFO)
            fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
            app.logger.addHandler(fh)
        app.logger.setLevel(logging.INFO)
    except Exception:
        pass

    return app
