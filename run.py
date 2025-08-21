# run.py
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import request, send_from_directory, jsonify

# نکته: همان ایمپورتی که الان در پروژه‌ات جواب می‌دهد را نگه می‌داریم
# اگر create_app در پکیج دیگری است، همین خط را مطابق ساختار خودت تغییر بده.
from app import create_app

app = create_app()

# ───────────────────────── لاگ‌گیری چرخشی ─────────────────────────
def _setup_logging(flask_app):
    try:
        logs_dir = os.path.join(flask_app.instance_path, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, "app.log")

        file_handler = RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

        flask_app.logger.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in flask_app.logger.handlers):
            flask_app.logger.addHandler(file_handler)

        # آرام کردن لاگر werkzeug (به‌خصوص برای 404های معمول)
        logging.getLogger("werkzeug").setLevel(logging.INFO)
    except Exception as e:
        # اگر لاگ‌گیری هم خطا داد، نگذاریم اپ نخوابد
        print("Log setup error:", e)

_setup_logging(app)

# ─────────────────────── favicon و استاتیک‌های رایج ───────────────────────
@app.route("/favicon.ico")
def _favicon():
    """اگر favicon موجود بود سرو می‌کنیم، وگرنه 204 تا لاگ خطا نخورد."""
    static_dir = os.path.join(app.root_path, "static")
    ico_path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(ico_path):
        return send_from_directory(static_dir, "favicon.ico", mimetype="image/vnd.microsoft.icon")
    return ("", 204)

# ───────────────────── هندلر 404 سبک برای استاتیک‌ها ─────────────────────
@app.errorhandler(404)
def _not_found(e):
    # برای مسیرهای استاتیک 404 را بی‌سروصدا برگردان تا لاگ شلوغ نشود
    if request.path.startswith("/static/"):
        return ("", 404)
    # برای سایر مسیرها JSON ساده (می‌توانی بعدا قالب 404.html اضافه کنی)
    return jsonify({"error": "Not Found", "path": request.path}), 404

# ───────────────────────── اجرای توسعه ─────────────────────────
if __name__ == "__main__":
    # نکته: در تولید حتماً از WSGI (مثل gunicorn/waitress) استفاده کن.
    app.run(
        debug=True,
        host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_RUN_PORT", "5000")),
    )
