# -*- coding: utf-8 -*-
"""
Uploads API for Vinor (vinor.ir)
- Endpoint: POST /api/uploads/images  → برمی‌گرداند: {"success": true, "id": "...", "url": "..."}
- Static serve: GET  /uploads/<path:filename>
- هماهنگ با CONFIG: app.config["UPLOAD_FOLDER"]
"""
from __future__ import annotations
import os
import uuid
import imghdr
from datetime import datetime
from typing import Tuple
from flask import Blueprint, current_app, request, jsonify, send_from_directory
from app.utils.storage import legacy_dir
from werkzeug.utils import secure_filename

uploads_bp = Blueprint("uploads", __name__)

# محدودیت‌ها
ALLOWED_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_SIZE_MB = 12  # با فرانت هماهنگ

def _ensure_folder(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _guess_ext_from_bytes(b: bytes) -> str:
    kind = imghdr.what(None, b)
    if kind == "jpeg":
        return "jpg"
    return kind or "jpg"

def _validate_file(fieldname: str = "file") -> Tuple[bytes, str]:
    """
    برمی‌گرداند: (file_bytes, ext) — در صورت خطا raise Exception
    """
    if fieldname not in request.files:
        raise ValueError("فایلی ارسال نشده است.")
    f = request.files[fieldname]
    if not f or f.filename == "":
        raise ValueError("نام فایل نامعتبر است.")

    raw = f.read()
    if not raw:
        raise ValueError("فایل خالی است.")

    # محدودیت حجم
    if len(raw) > MAX_SIZE_MB * 1024 * 1024:
        raise ValueError(f"حجم بیش از {MAX_SIZE_MB} مگابایت است.")

    ext = _guess_ext_from_bytes(raw)
    if ext not in ALLOWED_EXTS:
        # اگر حدس اشتباه بود، از پسوند امن‌شده استفاده کنیم
        original_ext = secure_filename(f.filename).rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if original_ext in ALLOWED_EXTS:
            ext = original_ext
        else:
            raise ValueError("فقط تصاویر مجاز هستند.")

    return raw, ext

@uploads_bp.post("/api/uploads/images")
def upload_image():
    """
    ذخیرهٔ تصویر و برگرداندن شناسه
    پاسخ استاندارد:
    {
      "success": true,
      "id": "2025/08/31/4d2f...e7.jpg",
      "url": "/uploads/2025/08/31/4d2f...e7.jpg"
    }
    """
    try:
        raw, ext = _validate_file("file")

        base_dir = current_app.config.get("UPLOAD_FOLDER")
        if not base_dir:
            return jsonify({"success": False, "error": "UPLOAD_FOLDER تنظیم نشده"}), 500

        # ساخت مسیر تاریخ‌محور: /YYYY/MM/DD/
        today = datetime.utcnow()
        rel_dir = os.path.join(str(today.year), f"{today.month:02d}", f"{today.day:02d}")
        abs_dir = os.path.join(base_dir, rel_dir)
        _ensure_folder(abs_dir)

        # نام یکتا
        uid = uuid.uuid4().hex
        filename = f"{uid}.{ext.lower()}"
        abs_path = os.path.join(abs_dir, filename)

        # نوشتن فایل
        with open(abs_path, "wb") as out:
            out.write(raw)

        rel_path = os.path.join(rel_dir, filename).replace("\\", "/")
        url = f"/uploads/{rel_path}"

        return jsonify({"success": True, "id": rel_path, "url": url})
    except Exception as e:
        current_app.logger.exception("Upload failed")
        return jsonify({"success": False, "error": str(e)}), 400

@uploads_bp.get("/uploads/<path:filename>")
def serve_uploads(filename: str):
    """
    سرو فایل‌های آپلود شده از UPLOAD_FOLDER.
    """
    base_dir = current_app.config.get("UPLOAD_FOLDER")
    if base_dir:
        safe_path = os.path.normpath(filename).replace("\\", "/")
        try:
            return send_from_directory(base_dir, safe_path)
        except Exception:
            pass
    # فالبک به مسیر قدیمی کنار کد
    legacy_base = os.path.join(legacy_dir(current_app), "uploads")
    safe_path = os.path.normpath(filename).replace("\\", "/")
    return send_from_directory(legacy_base, safe_path)
