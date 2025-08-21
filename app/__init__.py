# app/__init__.py
import os
from flask import Flask
from .filters import register_filters

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 🔑 حتماً یک secret_key ست کن (از env یا مقدار ثابت امن)
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    register_filters(app)

    # لود کردن همه‌ی روت‌ها از پکیج routes
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # بلوپرینت‌های مستقل
    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(webhook_bp)

    return app
