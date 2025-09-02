# app/__init__.py
# -*- coding: utf-8 -*-
"""
Vinor (vinor.ir) – Flask App Factory (Final)
- Mobile-first، امن و شفاف
- رجیستر بلوپرینت‌ها: main, admin, webhook, lands, uploads_api (آپلود) و push (اختیاری)
- سرو sw.js و manifest.webmanifest از ریشه (با fallback)
- گِیت پیمایش مهمان/کاربر
"""
import os
import logging
from datetime import timedelta
from flask import (
    Flask, request, redirect, url_for, session, current_app, send_from_directory
)

# فیلترهای Jinja
from .filters import register_filters

# CSRF (Flask-WTF)
try:
    from flask_wtf.csrf import CSRFProtect, CSRFError, generate_csrf
except Exception:
    CSRFProtect = None
    CSRFError = None
    def generate_csrf():  # fallback
        return ""

FIRST_VISIT_COOKIE = "vinor_first_visit_done"
SESSION_COOKIE_NAME = "vinor_session"


def _ensure_instance_folder(app: Flask) -> None:
    """ایجاد پوشه instance (برای لاگ‌ها/فایل‌های محلی)."""
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception as e:
        app.logger.warning("Cannot ensure instance folder: %s", e)


def _setup_logging(app: Flask) -> None:
    """نمایش INFO در کنسول حتی در Debug."""
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    handler.setFormatter(fmt)
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # ---------- پایه‌های امنیت/پیکربندی ----------
    # 🔑 کلید سشن (در پروداکشن از ENV بخوانید)
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    # مسیر پیش‌فرض آپلود (سیاست پروژه: app/data/uploads)
    default_upload_folder = os.path.join(app.root_path, "data", "uploads")
    os.makedirs(default_upload_folder, exist_ok=True)

    # مسیر ذخیره سابسکرایب پوش (اختیاری)
    default_push_store = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "push_subs.json")
    )

    # اگر روی HTTPS هستید (مثلاً روی سرور)، SESSION_COOKIE_SECURE=1 بگذارید
    cookie_secure = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    app.config.update(
        # Session / Cookies
        SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=180),
        PREFERRED_URL_SCHEME="https" if cookie_secure else "http",

        # Render/JSON
        TEMPLATES_AUTO_RELOAD=True,
        JSON_AS_ASCII=False,

        # Uploads
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", default_upload_folder),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 20MB

        # Push (اختیاری)
        VAPID_PUBLIC_KEY=os.environ.get("VAPID_PUBLIC_KEY", ""),
        VAPID_PRIVATE_KEY=os.environ.get("VAPID_PRIVATE_KEY", ""),
        VAPID_CLAIMS={"sub": os.environ.get("VAPID_SUB", "mailto:admin@vinor.ir")},
        PUSH_STORE_PATH=os.environ.get("PUSH_STORE_PATH", default_push_store),

        # Branding
        APP_BRAND_NAME="وینور | Vinor",

        # ✅ CSRF: سازگار با AJAX (در dev می‌توان بی‌انقضا گذاشت)
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,                  # در پروداکشن بهتر است عدد بگذارید (مثلاً 3600)
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_METHODS=("POST", "PUT", "PATCH", "DELETE"),
        # اگر پشت پروکسی/ساب‌دامین هستید و نیاز به اوریجین‌های خاص دارید:
        # WTF_CSRF_TRUSTED_ORIGINS=["https://vinor.ir", "https://www.vinor.ir"],
    )

    _ensure_instance_folder(app)
    _setup_logging(app)
    register_filters(app)

    # ---------- تزریق متغیرهای عمومی به Jinja ----------
    @app.context_processor
    def inject_vinor_globals():
        is_logged = bool(session.get("user_id") or session.get("user_phone"))
        return {
            "VAPID_PUBLIC_KEY": app.config.get("VAPID_PUBLIC_KEY", ""),
            "VINOR_IS_LOGGED_IN": is_logged,
            "VINOR_LOGIN_URL": url_for("main.login"),
            "APP_BRAND_NAME": app.config.get("APP_BRAND_NAME", "Vinor"),
            # برای {{ csrf_token() }} در فرم‌ها
            "csrf_token": generate_csrf,
        }

    # ---------- رجیستر بلوپرینت‌ها ----------
    from .routes import main_bp
    from .routes.admin import admin_bp
    from .routes.webhook import webhook_bp

    lands_bp = None
    try:
        from .routes.lands import lands_bp as _lands_bp
        lands_bp = _lands_bp
    except Exception as e:
        app.logger.warning(f"Lands routes not available: {e}")

    uploads_bp = None
    try:
        from .api.uploads import uploads_bp as _uploads_bp
        uploads_bp = _uploads_bp
    except Exception as e:
        app.logger.warning(f"Uploads API blueprint not available: {e}")

    push_bp = None
    try:
        from .api.push import push_bp as _push_bp
        push_bp = _push_bp
    except Exception as e:
        app.logger.warning(f"Push API disabled: {e}")

    app.register_blueprint(main_bp)                          # عمومی
    app.register_blueprint(admin_bp, url_prefix="/admin")    # ادمین
    app.register_blueprint(webhook_bp)                       # گیت‌وبهوک
    if lands_bp is not None:
        app.register_blueprint(lands_bp)                     # /lands/*
    if uploads_bp is not None:
        app.register_blueprint(uploads_bp)                   # /api/uploads/images + /uploads/...
    if push_bp is not None:
        app.register_blueprint(push_bp, url_prefix="/api/push")

    # ---------- CSRFProtect: فعال + معافیت‌های لازم ----------
    if CSRFProtect is not None:
        csrf = CSRFProtect()
        csrf.init_app(app)

        # webhook (از CSRF معاف شود)
        try:
            from .routes.webhook import git_webhook
            csrf.exempt(git_webhook)
        except Exception:
            csrf.exempt(webhook_bp)

        # اگر با آپلود یا پوش خطای CSRF دارید، در صورت نیاز معاف کنید:
        # if uploads_bp is not None:
        #     csrf.exempt(uploads_bp)
        # if push_bp is not None:
        #     csrf.exempt(push_bp)

        # ست کوکی قابل‌خواندن برای AJAX (XSRF)
        @app.after_request
        def set_csrf_cookie(resp):
            try:
                token = generate_csrf()
                resp.set_cookie(
                    "XSRF-TOKEN",
                    token,
                    secure=cookie_secure,
                    samesite="Lax",
                    httponly=False,     # باید قابل خواندن توسط JS باشد
                    path="/",
                    max_age=60 * 60 * 24 * 7  # صرفاً برای راحتی؛ انقضای فرم None است
                )
            except Exception:
                pass
            return resp

        # هندلر خطا برای تجربهٔ بهتر کاربر + لاگ دقیق
        if CSRFError is not None:
            @app.errorhandler(CSRFError)
            def handle_csrf_error(e):
                from flask import flash
                current_app.logger.error(
                    "CSRF_ERROR: %s | path=%s | form=%s | headers=%s",
                    getattr(e, "description", str(e)),
                    request.path,
                    dict(request.form),
                    dict(request.headers),
                )
                flash("⚠️ اعتبار فرم به پایان رسیده یا هماهنگ نیست. صفحه را تازه کنید و دوباره تلاش کنید.", "warning")
                # برگشت به صفحه قبلی یا صفحه افزودن آگهی (برای UX بهتر)
                try:
                    return redirect(request.referrer or url_for("lands.add_land"))
                except Exception:
                    return redirect(request.referrer or url_for("main.index"))

    # ---------- سرویس مستقیم فایل‌های PWA از ریشه ----------
    @app.get("/sw.js")
    def service_worker():
        static_dir = os.path.join(app.root_path, "static")
        return send_from_directory(static_dir, "sw.js", mimetype="application/javascript")

    @app.get("/manifest.webmanifest")
    def serve_manifest():
        """
        Serve manifest from /app/static; fallback to inlined JSON if file missing.
        جلوگیری از 404 حتی در نبود فایل روی دیسک.
        """
        from flask import Response
        static_dir = os.path.join(app.root_path, "static")
        file_path = os.path.join(static_dir, "manifest.webmanifest")
        mimetype = "application/manifest+json"

        current_app.logger.info("Manifest lookup at: %s", file_path)

        if os.path.exists(file_path):
            return send_from_directory(static_dir, "manifest.webmanifest", mimetype=mimetype)

        # --- Fallback JSON (مینیمال و معتبر) ---
        fallback_json = r'''{
          "id": "/app",
          "name": "وینور | بازار آنلاین ملک",
          "short_name": "وینور",
          "description": "وینور؛ تجربه سریع، امن و شفاف برای خرید و فروش زمین، باغ، ویلا و آپارتمان.",
          "dir": "rtl",
          "lang": "fa",
          "start_url": "/app?source=pwa",
          "scope": "/",
          "display": "standalone",
          "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
          "orientation": "portrait",
          "background_color": "#ffffff",
          "theme_color": "#16a34a",
          "icons": [
            { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
            { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
          ],
          "shortcuts": [
            { "name": "ثبت آگهی رایگان", "short_name": "ثبت آگهی", "url": "/submit-ad" },
            { "name": "آگهی‌های من", "short_name": "آگهی‌ها", "url": "/my-lands" }
          ],
          "capture_links": "existing-client-navigate",
          "launch_handler": { "client_mode": "auto" }
        }'''
        return Response(fallback_json, status=200, mimetype=mimetype)

    # ---------- سیاست پیمایش (Gate) ----------
    @app.before_request
    def landing_gate():
        """
        - /static, /api, /admin, /diagnostics, /uploads آزاد
        - مسیرهای عمومی آزاد
        - کاربر لاگین: عبور
        - کاربر مهمان: اول به لندینگ، سپس به لاگین
        """
        # Prefixهای امن
        safe_prefixes = ("/static", "/api", "/admin", "/diagnostics", "/uploads")
        if request.path.startswith(safe_prefixes):
            current_app.logger.debug("PASS (prefix): %s", request.path)
            return

        # مسیرهای عمومی
        safe_paths = {
            "/", "/start", "/login", "/verify", "/logout",
            "/favicon.ico", "/robots.txt", "/sitemap.xml",
            "/site.webmanifest", "/manifest.webmanifest", "/sw.js",
            "/git-webhook", "/git-webhook/",
        }
        if request.path in safe_paths:
            current_app.logger.debug("PASS (path): %s", request.path)
            return

        user_logged_in = bool(session.get("user_id") or session.get("user_phone"))
        has_seen_landing = (request.cookies.get(FIRST_VISIT_COOKIE) == "1")

        if user_logged_in:
            current_app.logger.debug("PASS (logged-in): %s", request.path)
            return

        if not has_seen_landing:
            current_app.logger.debug("REDIRECT → / (first-visit): %s", request.path)
            return redirect(url_for("main.index"))
        else:
            current_app.logger.debug("REDIRECT → /login (guest): %s", request.path)
            return redirect(url_for("main.login"))

    # ---------- جلوگیری از کش فرم افزودن آگهی ----------
    @app.after_request
    def _vinor_no_store_for_forms(resp):
        try:
            if request.method == "GET" and request.path.rstrip("/") in ("/lands/add",):
                resp.headers["Cache-Control"] = "no-store"
        except Exception:
            pass
        return resp

    return app
