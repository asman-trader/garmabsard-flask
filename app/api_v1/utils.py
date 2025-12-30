from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional, Tuple

import jwt
from flask import current_app, jsonify, request

PHONE_RE = re.compile(r"^09\d{9}$")

_otp_rate_limit: Dict[str, list] = {}  # phone -> [timestamps]
_otp_store: Dict[str, Tuple[str, float]] = {}  # phone -> (code, expires_ts)


def api_response(success: bool, data: Any = None, error: Any = None, meta: Any = None, status: int = 200):
    payload: Dict[str, Any] = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status


def _get_jwt_secret() -> str:
    return os.environ.get("JWT_SECRET") or current_app.config.get("SECRET_KEY") or "change-me"


def create_jwt(user_id: int, phone: str, ttl_minutes: int = 60 * 24 * 14) -> str:
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": str(user_id),
        "uid": user_id,
        "phone": phone,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")
    return token


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        return payload
    except Exception:
        return None


def get_auth_user_id() -> Optional[int]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_jwt(token)
    if not payload:
        return None
    try:
        return int(payload.get("uid"))
    except Exception:
        return None


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = get_auth_user_id()
        if not uid:
            return api_response(False, error={"message": "Unauthorized"}, status=401)
        return fn(*args, **kwargs, auth_user_id=uid)

    return wrapper


def validate_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone or ""))


def otp_can_request(phone: str) -> Tuple[bool, Optional[str]]:
    now = time.time()
    lst = _otp_rate_limit.get(phone, [])
    # allow 1 per 60s, 5 per hour
    lst = [t for t in lst if now - t < 3600]
    _otp_rate_limit[phone] = lst
    if lst and now - lst[-1] < 60:
        return False, "لطفاً ۶۰ ثانیه صبر کنید."
    if len(lst) >= 5:
        return False, "تلاش بیش از حد. بعداً تلاش کنید."
    return True, None


def otp_register_request(phone: str) -> None:
    now = time.time()
    _otp_rate_limit.setdefault(phone, []).append(now)


def otp_set_code(phone: str, code: str, ttl_seconds: int = 180) -> None:
    exp = time.time() + ttl_seconds
    _otp_store[phone] = (code, exp)


def otp_verify_code(phone: str, code: str) -> bool:
    item = _otp_store.get(phone)
    if not item:
        return False
    saved_code, exp = item
    if time.time() > exp:
        _otp_store.pop(phone, None)
        return False
    ok = saved_code == code
    if ok:
        _otp_store.pop(phone, None)
    return ok


def paginate_query(query, page: int, page_size: int):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    total = query.count()
    items = (
        query.order_by(getattr(query._entities[0].entity_zero.class_, "created_at", None).desc() if hasattr(query._entities[0].entity_zero.class_, "created_at") else None)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = (total + page_size - 1) // page_size if page_size else 1
    return items, {"page": page, "page_size": page_size, "total": total, "pages": pages}


def file_url_for(path_abs: str) -> str:
    try:
        uploads_root = current_app.config.get("UPLOAD_FOLDER")
        rel = path_abs.replace(uploads_root, "").lstrip("/\\")
        return f"/uploads/{rel.replace('\\', '/')}"
    except Exception:
        return ""


ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}


def is_allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_IMAGE_EXT


