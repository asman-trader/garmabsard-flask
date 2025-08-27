# app/__init__.py
import os
from datetime import timedelta
from flask import Flask, request, redirect, url_for, session

# رجیستر فیلترهای Jinja در سطح اپ (جلوگیری از import loop)
from .filters import register_filters

FIRST_VISIT_COOKIE = "vinor_first_visit_done"


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 🔑 کلید سشن (در پروداکشن از ENV بخوانید)
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    # ⚙️ تنظیمات پایه سشن/کوکی
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,  # اگر فقط HTTPS دارید True کنید
        PERMANENT_SESSION_LIFETIME=timedelta(days=180),
    )

    # 🧩 فیلترهای Jinja
    register_filters(app)

    # 🧭 بلوپرینت‌ها
    from .routes import main_bp
    app.register_blueprint(main_bp)  # روت‌های عمومی (شامل / و /app و ...)

    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(webhook_bp)

    # 🚧 گیت سراسری: نمایش لندینگ فقط یک‌بار (Cookie-based)
    @app.before_request
    def landing_gate():
        """
        سیاست پیمایش:
        - مسیرهای امن/استاتیک/سیستمی آزادند.
        - '/' و '/start' و مسیرهای ورود همیشه آزادند.
        - اگر کاربر وارد است → عبور.
        - اگر وارد نیست و هنوز لندینگ را ندیده → هدایت به لندینگ.
        - اگر وارد نیست و لندینگ را دیده → هدایت به صفحه ورود.
        """
        # مسیرهایی که نباید محدود شوند (استاتیک/وبهوک/ادمین/آپلودها/تشخیصی)
        safe_prefixes = (
            "/static",
            "/api",
            "/webhook",
            "/admin",
            "/diagnostics",
            "/uploads",
        )
        if request.path.startswith(safe_prefixes):
            return  # اجازه عبور

        # مسیرهای عمومی که همیشه آزادند
        safe_paths = {
            "/",           # لندینگ
            "/start",      # CTA لندینگ
            "/login",      # ورود (main.login)
            "/verify",     # تایید OTP (main.verify)
            "/logout",     # خروج
            "/favicon.ico",
            "/robots.txt",
            "/sitemap.xml",
            "/site.webmanifest",
        }
        if request.path in safe_paths:
            return

        user_logged_in = bool(session.get("user_id"))
        has_seen_landing = (request.cookies.get(FIRST_VISIT_COOKIE) == "1")

        if user_logged_in:
            return  # کاربر وارد است → ادامه مسیر

        if not has_seen_landing:
            # اولین بازدید: هدایت به لندینگ (زیر main_bp)
            return redirect(url_for("main.index"))
        else:
            # قبلاً لندینگ را دیده اما وارد نیست: هدایت به صفحه ورود
            return redirect(url_for("main.login"))

    return app
