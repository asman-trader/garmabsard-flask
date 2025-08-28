# app/__init__.py
# -*- coding: utf-8 -*-
"""
Vinor (vinor.ir) – Flask App Factory (Final)
- Mobile‑first, امن و شفاف بر مبنای سشن و گِیت پیمایش
- ایمن‌سازی importهای بلوپرینت و Push API
- ثبت فیلترهای Jinja و تزریق مقادیر سراسری برای PWA/Push
"""
import os
import logging
from datetime import timedelta
from flask import (
    Flask, request, redirect, url_for, session, current_app, send_from_directory
)

# رجیستر فیلترهای Jinja در سطح اپ (جلوگیری از import loop)
from .filters import register_filters

# ثوابت کوکی و سشن
FIRST_VISIT_COOKIE = "vinor_first_visit_done"
SESSION_COOKIE_NAME = "vinor_session"


# -------------------------
# Utils
# -------------------------
def _ensure_instance_folder(app: Flask) -> None:
    """ایجاد خودکار پوشه instance (برای لاگ/فایل‌های محلی)."""
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception as e:
        app.logger.warning("Cannot ensure instance folder: %s", e)


def _setup_logging(app: Flask) -> None:
    """تنظیم لاگر برای محیط هاست/WGSI (بدون تداخل با حالت دیباگ)."""
    if not app.debug and not app.testing:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        handler.setFormatter(fmt)
        # جلوگیری از افزودن هندلر تکراری
        if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
            app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)


# -------------------------
# App Factory
# -------------------------
def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # 🔑 کلید سشن (در پروداکشن از ENV بخوانید)
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    # مسیر پیش‌فرض ذخیره سابسکرایب‌ها (قابل override با ENV)
    default_push_store = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "push_subs.json")
    )

    # ⚙️ تنظیمات پایه سشن/کوکی و پوش
    cookie_secure = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.config.update(
        SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,  # برای HTTPS واقعی مقدار 1 بگذارید
        PERMANENT_SESSION_LIFETIME=timedelta(days=180),
        PREFERRED_URL_SCHEME="https" if cookie_secure else "http",

        # 🔔 کلیدهای VAPID برای Web Push (از ENV بخوان؛ در صورت نبود، خالی می‌ماند)
        VAPID_PUBLIC_KEY=os.environ.get("VAPID_PUBLIC_KEY", ""),
        VAPID_PRIVATE_KEY=os.environ.get("VAPID_PRIVATE_KEY", ""),
        VAPID_CLAIMS={"sub": os.environ.get("VAPID_SUB", "mailto:admin@vinor.ir")},

        # مسیر فایل ذخیره سابسکرایب‌ها
        PUSH_STORE_PATH=os.environ.get("PUSH_STORE_PATH", default_push_store),

        # (اختیاری) عنوان اپ برای استفاده در قالب‌ها
        APP_BRAND_NAME="وینور | Vinor",
    )

    # 🗂️ آماده‌سازی پوشه instance و لاگر
    _ensure_instance_folder(app)
    _setup_logging(app)

    # 🧩 فیلترهای Jinja
    register_filters(app)

    # --- Inject globals into Jinja templates (برای دسترسی در base.html و سایر قالب‌ها) ---
    @app.context_processor
    def inject_vinor_globals():
        return {
            "VAPID_PUBLIC_KEY": app.config.get("VAPID_PUBLIC_KEY", ""),
            "VINOR_IS_LOGGED_IN": bool(session.get("user_id")),
            "VINOR_LOGIN_URL": url_for("main.login"),
            "APP_BRAND_NAME": app.config.get("APP_BRAND_NAME", "Vinor"),
        }

    # 🧭 ثبت بلوپرینت‌ها (import درون تابع برای جلوگیری از import loop)
    from .routes import main_bp
    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp

    # Push API را محافظه‌کارانه ثبت می‌کنیم تا نبودن وابستگی‌ها باعث Fail نشود
    push_bp = None
    try:
        from .api.push import push_bp as _push_bp
        push_bp = _push_bp
    except Exception as e:
        app.logger.warning(f"Push API disabled: {e}")

    # ثبت
    app.register_blueprint(main_bp)                         # روت‌های عمومی (/ ، /app ، ...)
    app.register_blueprint(admin_bp, url_prefix="/admin")  # پنل ادمین
    app.register_blueprint(webhook_bp)                      # /git-webhook
    if push_bp is not None:
        app.register_blueprint(push_bp, url_prefix="/api/push")  # /api/push/*

    # (اختیاری) راه‌اندازی CSRF اگر Flask-WTF نصب باشد + معافیت وبهوک
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect()
        csrf.init_app(app)
        try:
            from .routes.webhook import git_webhook
            csrf.exempt(git_webhook)
        except Exception:
            csrf.exempt(webhook_bp)
        # اگر لازم شد API پوش هم معاف شود:
        # if push_bp is not None:
        #     csrf.exempt(push_bp)
    except Exception:
        # اگر Flask-WTF نصب نبود، بی‌صدا ادامه بده
        pass

    # ⚡ سرویس مستقیم Service Worker از ریشه دامنه: /sw.js
    # فایل sw.js را در پوشه /app/static قرار دهید.
    @app.get("/sw.js")
    def service_worker():
        static_dir = os.path.join(app.root_path, "static")
        return send_from_directory(static_dir, "sw.js", mimetype="application/javascript")

    # 🚧 گِیت سراسری: سیاست پیمایش مهمان/کاربر + معافیت‌ها
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
        # مسیرهایی که نباید محدود شوند (استاتیک/وبهوک/ادمین/آپلودها/تشخیصی/API)
        safe_prefixes = (
            "/static",
            "/api",
            "/admin",
            "/diagnostics",
            "/uploads",
        )
        if request.path.startswith(safe_prefixes):
            current_app.logger.debug("PASS (prefix): %s", request.path)
            return

        # مسیرهای عمومی که همیشه آزادند + معافیت‌های صریح
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
            "/sw.js",              # Service Worker باید از ریشه آزاد باشد
            "/git-webhook",        # وبهوک GitHub
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
