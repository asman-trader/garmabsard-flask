# app/__init__.py
import os
from datetime import timedelta
from flask import Flask, request, redirect, url_for, session, current_app

# رجیستر فیلترهای Jinja در سطح اپ (جلوگیری از import loop)
from .filters import register_filters

FIRST_VISIT_COOKIE = "vinor_first_visit_done"


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 🔑 کلید سشن (در پروداکشن از ENV بخوانید)
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    # ⚙️ تنظیمات پایه سشن/کوکی
    cookie_secure = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,  # برای HTTPS واقعی مقدار 1 بگذارید
        PERMANENT_SESSION_LIFETIME=timedelta(days=180),
    )

    # 🧩 فیلترهای Jinja
    register_filters(app)

    # 🧭 بلوپرینت‌ها
    from .routes import main_bp
    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp

    app.register_blueprint(main_bp)                    # روت‌های عمومی (/ ، /app ، ...)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(webhook_bp)                 # url_prefix="/webhook"

    # 🚧 گِیت سراسری: کنترل پیمایش مهمان/کاربر + معافیت کامل وبهوک
    @app.before_request
    def landing_gate():
        """
        سیاست پیمایش:
        - مسیرهای امن/سیستمی/وبهوک آزادند.
        - '/' و '/start' و مسیرهای ورود همیشه آزادند.
        - اگر کاربر وارد است → عبور.
        - اگر وارد نیست و هنوز لندینگ را ندیده → هدایت به لندینگ.
        - اگر وارد نیست و لندینگ را دیده → هدایت به صفحه ورود.
        """
        # مسیرهایی که نباید محدود شوند (استاتیک/وبهوک/ادمین/آپلودها/تشخیصی/ API)
        safe_prefixes = (
            "/static",
            "/api",
            "/webhook",      # 👈 تمامی وبهوک‌ها (POST/GET) معاف
            "/admin",
            "/diagnostics",
            "/uploads",
        )
        if request.path.startswith(safe_prefixes):
            current_app.logger.debug("PASS (prefix): %s", request.path)
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
            # کمربند ایمنی برای وبهوک‌های بدون زیرمسیر
            "/webhook",
            "/webhook/",
        }
        if request.path in safe_paths:
            current_app.logger.debug("PASS (path): %s", request.path)
            return

        user_logged_in = bool(session.get("user_id"))
        has_seen_landing = (request.cookies.get(FIRST_VISIT_COOKIE) == "1")

        if user_logged_in:
            current_app.logger.debug("PASS (logged-in): %s", request.path)
            return  # کاربر وارد است → ادامه مسیر

        if not has_seen_landing:
            current_app.logger.debug("REDIRECT → / (first-visit): %s", request.path)
            return redirect(url_for("main.index"))  # اولین بازدید: لندینگ
        else:
            current_app.logger.debug("REDIRECT → /login (guest): %s", request.path)
            return redirect(url_for("main.login"))  # مهمان: صفحه ورود

    return app
