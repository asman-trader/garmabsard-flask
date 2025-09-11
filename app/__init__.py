# app/__init__.py
# -*- coding: utf-8 -*-
"""
Vinor (vinor.ir) – Flask App Factory (Final)
- Mobile-first، امن و شفاف
- رجیستر بلوپرینت‌ها: main, admin, webhook, lands (اختیاری), uploads_api (اختیاری), push (اختیاری)
- سرو sw.js و manifest.webmanifest از ریشه (با fallback)
- گِیت پیمایش مهمان/کاربر
"""
import os
import logging
from datetime import timedelta, datetime
from flask import (
    Flask, request, redirect, url_for, session, current_app, send_from_directory
)

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
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception as e:
        app.logger.warning("Cannot ensure instance folder: %s", e)


def _setup_logging(app: Flask) -> None:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    handler.setFormatter(fmt)
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _register_jinja_filters(app: Flask) -> None:
    """ثبت فیلترهای Jinja موردنیاز پروژه: time_ago، date_ymd، your_time_filter، basename."""
    def _parse_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except Exception:
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except Exception:
                pass
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, fmt)
                except Exception:
                    continue
        return None

    @app.template_filter("time_ago")
    def time_ago(value):
        dt = _parse_dt(value)
        if dt is None:
            return ""
        now = datetime.now(dt.tzinfo) if getattr(dt, "tzinfo", None) else datetime.now()
        diff = now - dt
        s = int(diff.total_seconds())
        if s < 60:
            return "چند لحظه پیش"
        m = s // 60
        if m < 60:
            return f"{m} دقیقه پیش"
        h = m // 60
        if h < 24:
            return f"{h} ساعت پیش"
        d = h // 24
        if d < 30:
            return f"{d} روز پیش"
        mo = d // 30
        if mo < 12:
            return f"{mo} ماه پیش"
        y = mo // 12
        return f"{y} سال پیش"

    @app.template_filter("date_ymd")
    def date_ymd(value, sep="-"):
        dt = _parse_dt(value)
        if dt is None:
            return ""
        return dt.strftime(f"%Y{sep}%m{sep}%d")

    @app.template_filter("your_time_filter")
    def your_time_filter(value):
        return time_ago(value)

    @app.template_filter("basename")
    def basename_filter(value):
        try:
            return os.path.basename(str(value)) if value is not None else ""
        except Exception:
            return ""


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # ---------- پایه‌های امنیت/پیکربندی ----------
    app.secret_key = os.environ.get("SECRET_KEY") or "super-secret-key-change-this"

    default_upload_folder = os.path.join(app.root_path, "data", "uploads")
    os.makedirs(default_upload_folder, exist_ok=True)

    default_push_store = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "push_subs.json")
    )

    cookie_secure = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    vapid_sub = os.environ.get("VAPID_SUB", "mailto:admin@vinor.ir")

    app.config.update(
        SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=180),
        PREFERRED_URL_SCHEME="https" if cookie_secure else "http",
        TEMPLATES_AUTO_RELOAD=True,
        JSON_AS_ASCII=False,
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", default_upload_folder),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 20MB
        VAPID_PUBLIC_KEY=os.environ.get("VAPID_PUBLIC_KEY", ""),
        VAPID_PRIVATE_KEY=os.environ.get("VAPID_PRIVATE_KEY", ""),
        # هر دو کلید برای سازگاری: dict و زیرکلید متنی
        VAPID_CLAIMS={"sub": vapid_sub},
        VAPID_CLAIMS_SUB=vapid_sub,
        PUSH_STORE_PATH=os.environ.get("PUSH_STORE_PATH", default_push_store),
        APP_BRAND_NAME="وینور | Vinor",
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_METHODS=("POST", "PUT", "PATCH", "DELETE"),
    )

    _ensure_instance_folder(app)
    _setup_logging(app)
    _register_jinja_filters(app)

    @app.context_processor
    def inject_vinor_globals():
        is_logged = bool(session.get("user_id") or session.get("user_phone"))
        return {
            "VAPID_PUBLIC_KEY": app.config.get("VAPID_PUBLIC_KEY", ""),
            "VINOR_IS_LOGGED_IN": is_logged,
            "VINOR_LOGIN_URL": url_for("main.login"),
            "APP_BRAND_NAME": app.config.get("APP_BRAND_NAME", "Vinor"),
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
        # سازگاری با alias
        from .api.push import push_bp as _push_bp
        push_bp = _push_bp
    except Exception as e:
        app.logger.warning(f"Push API disabled: {e}")

    # توجه: هیچ url_prefix اضافی نده؛ هر بلوپرینت خودش دارد.
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(webhook_bp)
    if lands_bp is not None:
        app.register_blueprint(lands_bp)
    if uploads_bp is not None:
        app.register_blueprint(uploads_bp)
    if push_bp is not None:
        app.register_blueprint(push_bp)

    # ---------- CSRF ----------
    if CSRFProtect is not None:
        csrf = CSRFProtect()
        csrf.init_app(app)

        try:
            from .routes.webhook import git_webhook
            csrf.exempt(git_webhook)
        except Exception:
            csrf.exempt(webhook_bp)

        # APIهایی که از طریق AJAX فراخوانی می‌شوند را از CSRF مستثنا می‌کنیم (آپلود تصاویر)
        try:
            if uploads_bp is not None:
                csrf.exempt(uploads_bp)
        except Exception:
            pass

        @app.after_request
        def set_csrf_cookie(resp):
            try:
                token = generate_csrf()
                resp.set_cookie(
                    "XSRF-TOKEN",
                    token,
                    secure=app.config.get("SESSION_COOKIE_SECURE", False),
                    samesite="Lax",
                    httponly=False,
                    path="/",
                    max_age=60 * 60 * 24 * 7,
                )
            except Exception:
                pass
            return resp

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
                try:
                    return redirect(request.referrer or url_for("lands.add_land"))
                except Exception:
                    return redirect(url_for("main.index"))

    # ---------- فایل‌های PWA ----------
    @app.get("/sw.js")
    def service_worker():
        # برای سازگاری: سرو sw.js از static
        static_dir = os.path.join(app.root_path, "static")
        return send_from_directory(static_dir, "sw.js", mimetype="application/javascript")

    @app.get("/manifest.webmanifest")
    def serve_manifest():
        from flask import Response
        static_dir = os.path.join(app.root_path, "static")
        file_path = os.path.join(static_dir, "manifest.webmanifest")
        mimetype = "application/manifest+json"

        current_app.logger.info("Manifest lookup at: %s", file_path)

        if os.path.exists(file_path):
            return send_from_directory(static_dir, "manifest.webmanifest", mimetype=mimetype)

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

    # ---------- Gate ----------
    @app.before_request
    def landing_gate():
        safe_prefixes = ("/static", "/api", "/admin", "/diagnostics", "/uploads")
        if request.path.startswith(safe_prefixes):
            current_app.logger.debug("PASS (prefix): %s", request.path)
            return

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
