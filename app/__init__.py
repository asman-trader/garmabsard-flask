# app/__init__.py
# -*- coding: utf-8 -*-
import os
import logging
from datetime import timedelta
from flask import Flask, request, redirect, url_for, session, current_app

# رجیستر فیلترهای Jinja در سطح اپ (جلوگیری از import loop)
from .filters import register_filters


FIRST_VISIT_COOKIE = "vinor_first_visit_done"
SESSION_COOKIE_NAME = "vinor_session"


def _ensure_instance_folder(app: Flask) -> None:
    """ایجاد خودکار پوشه instance در صورت نبودن (برای لاگ‌ها/فایل‌های محلی)."""
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception as e:
        app.logger.warning("Cannot ensure instance folder: %s", e)


def _setup_logging(app: Flask) -> None:
    """تنظیم لاگر اپ برای محیط هاست (WSGI)."""
    if not app.debug and not app.testing:
        # ساده: لاگ به استریم استاندارد (توسط WSGI جمع‌آوری می‌شود)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        handler.setFormatter(fmt)
        if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
            app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # 🔑 کلید سشن (در پروداکشن از ENV بخوانید)
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    # ⚙️ تنظیمات پایه سشن/کوکی
    cookie_secure = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.config.update(
        SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,  # برای HTTPS واقعی مقدار 1 بگذارید
        PERMANENT_SESSION_LIFETIME=timedelta(days=180),
        PREFERRED_URL_SCHEME="https" if cookie_secure else "http",
    )

    # 🗂️ آماده‌سازی پوشه instance و لاگر
    _ensure_instance_folder(app)
    _setup_logging(app)

    # 🧩 فیلترهای Jinja
    register_filters(app)

    # 🧭 بلوپرینت‌ها
    # نکته: import‌ها را اینجا انجام می‌دهیم تا از import loop جلوگیری شود.
    from .routes import main_bp
    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp
    # اگر نیاز به معافیت CSRF داریم، در ادامه هندل می‌شود.

    app.register_blueprint(main_bp)                    # روت‌های عمومی (/ ، /app ، ...)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(webhook_bp)                 # /git-webhook

    # (اختیاری) راه‌اندازی CSRF فقط اگر Flask-WTF نصب باشد
    # و معاف‌کردن روت وب‌هوک از CSRF (برای درخواست‌های GitHub)
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect()
        csrf.init_app(app)

        # تلاش برای معاف‌کردن تنها ویوی وبهوک
        try:
            # import محلی برای گرفتن تابع ویو
            from .routes.webhook import git_webhook
            csrf.exempt(git_webhook)
        except Exception:
            # اگر تابع در دسترس نبود، کل بلوپرینت را معاف کن
            csrf.exempt(webhook_bp)
    except Exception:
        # Flask-WTF نصب نیست؛ مشکلی نیست، ادامه می‌دهیم.
        pass

    # 🚧 گِیت سراسری: کنترل پیمایش مهمان/کاربر + معافیت کامل وبهوک
    @app.before_request
    def landing_gate():
        """
        سیاست پیمایش Vinor (سریع، امن، شفاف):
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
            "/admin",
            "/diagnostics",
            "/uploads",
        )
        if request.path.startswith(safe_prefixes):
            current_app.logger.debug("PASS (prefix): %s", request.path)
            return  # اجازه عبور

        # مسیرهای عمومی که همیشه آزادند + معافیت صریح وبهوک
        safe_paths = {
            "/",                   # لندینگ
            "/start",              # CTA لندینگ
            "/login",              # ورود (main.login)
            "/verify",             # تایید OTP (main.verify)
            "/logout",             # خروج
            "/favicon.ico",
            "/robots.txt",
            "/sitemap.xml",
            "/site.webmanifest",
            # 👇 وبهوک GitHub باید کاملاً آزاد باشد (بدون ریدایرکت)
            "/git-webhook",
            "/git-webhook/",
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
