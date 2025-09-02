# -*- coding: utf-8 -*-
"""
Vinor API – Image Uploads
- مسیر اصلی آپلود: POST /api/uploads/images  (FormData: file)
- سرو فایل آپلود شده:  GET  /uploads/<YYYYMMDD>/<filename>
- خروجی سازگار با فرانت: { ok, id, filename, url }
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import Tuple

from flask import (
    Blueprint, current_app, jsonify, request, url_for, send_from_directory, abort
)
from werkzeug.utils import secure_filename

api_bp = Blueprint("api", __name__)

# پسوندهای مجاز و محدودیت‌ها
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_FILE_SIZE_MB = 16  # اگر خواستی از ENV بخون: int(os.environ.get("VINOR_MAX_IMG_MB", "16"))

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def _allowed(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXT

def _get_upload_root() -> str:
    """
    مسیر ریشه آپلود را از کانفیگ می‌خوانیم (در __init__.py ست شده).
    پیش‌فرض: app/data/uploads
    """
    root = current_app.config.get("UPLOAD_FOLDER")
    if not root:
        root = os.path.join(current_app.root_path, "data", "uploads")
    os.makedirs(root, exist_ok=True)
    return root

def _date_dir_path(root: str) -> Tuple[str, str]:
    """
    ساخت و برگرداندن مسیر پوشه تاریخ‌دار (UTC) مثل 20250831
    """
    date_dir = datetime.utcnow().strftime("%Y%m%d")
    target = os.path.join(root, date_dir)
    os.makedirs(target, exist_ok=True)
    return date_dir, target

def _limit_size(file_storage) -> bool:
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size <= MAX_FILE_SIZE_MB * 1024 * 1024

def _json_error(code: int, msg: str):
    return jsonify({"ok": False, "error": msg}), code

# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@api_bp.post("/api/uploads/images")
def upload_image():
    """
    آپلود تکی تصویر.
    ورودی: FormData → key: 'file'
    خروجی موفق: { ok: True, id, filename: "<YYYYMMDD>/<name.ext>", url: "/uploads/..." }
    """
    if "file" not in request.files:
        return _json_error(400, "NO_FILE")

    f = request.files["file"]
    if not f or f.filename == "":
        return _json_error(400, "EMPTY_NAME")

    if not _allowed(f.filename):
        return _json_error(400, "BAD_EXT")

    if not _limit_size(f):
        return _json_error(400, "FILE_TOO_LARGE")

    upload_root = _get_upload_root()
    date_dir, target_dir = _date_dir_path(upload_root)

    original = secure_filename(f.filename)
    ext = original.rsplit(".", 1)[-1].lower()
    uid = uuid.uuid4().hex
    filename = f"{uid}.{ext}"
    path = os.path.join(target_dir, filename)

    try:
        f.save(path)
    except Exception as e:
        current_app.logger.exception("Upload save failed: %s", e)
        return _json_error(500, "SAVE_FAILED")

    public_url = url_for("api.uploads_serve", date=date_dir, filename=filename, _external=False)

    # خروجی سازگار با کد فرانت (id / file_id / uuid هر سه قابل استفاده)
    return jsonify({
        "ok": True,
        "id": uid,
        "file_id": uid,
        "uuid": uid,
        "filename": f"{date_dir}/{filename}",
        "url": public_url
    }), 200


@api_bp.get("/uploads/<date>/<path:filename>")
def uploads_serve(date: str, filename: str):
    """
    سرو فایل‌های آپلود شده (فقط خواندنی).
    توجه: اگر نیاز به کنترل دسترسی داری، اینجا اضافه کن.
    """
    upload_root = _get_upload_root()
    directory = os.path.join(upload_root, date)
    if not os.path.isdir(directory):
        abort(404)
    return send_from_directory(directory, filename, as_attachment=False)
