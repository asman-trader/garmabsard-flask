# app/__init__.py
import os
from flask import Flask
from .filters import register_filters

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.setdefault("SECRET_KEY", os.environ.get("SECRET_KEY", "dev-key"))
    register_filters(app)

    # این import، کل پکیج routes را لود می‌کند و چون
    # داخل routes/__init__.py ماژول‌ها import شده‌اند،
    # همه‌ی روت‌ها قبل از register آماده‌اند.
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # بلوپرینت‌های مستقل
    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(webhook_bp)

    return app
