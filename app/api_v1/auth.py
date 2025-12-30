from __future__ import annotations

import random

from flask import request

from . import api_v1_bp
from .models import User
from ..extensions import db
from .utils import (
    api_response,
    auth_required,
    create_jwt,
    otp_can_request,
    otp_register_request,
    otp_set_code,
    otp_verify_code,
    validate_phone,
)


@api_v1_bp.post("/auth/request-otp")
def request_otp():
    payload = request.get_json(silent=True) or {}
    phone = str(payload.get("phone", "")).strip()
    if not validate_phone(phone):
        return api_response(False, error={"message": "شماره موبایل نامعتبر است."}, status=400)
    ok, reason = otp_can_request(phone)
    if not ok:
        return api_response(False, error={"message": reason}, status=429)
    otp_register_request(phone)
    code = "".join(str(random.randint(0, 9)) for _ in range(5))
    otp_set_code(phone, code, ttl_seconds=180)
    # TODO: integrate with SMS provider; in development, include code in meta
    return api_response(True, data={"sent": True}, meta={"debug_code": code})


@api_v1_bp.post("/auth/verify-otp")
def verify_otp():
    payload = request.get_json(silent=True) or {}
    phone = str(payload.get("phone", "")).strip()
    code = str(payload.get("code", "")).strip()
    if not (validate_phone(phone) and code and code.isdigit()):
        return api_response(False, error={"message": "داده‌های ورود نامعتبر است."}, status=400)
    if not otp_verify_code(phone, code):
        return api_response(False, error={"message": "کد یکبار مصرف اشتباه یا منقضی است."}, status=400)
    user = User.query.filter_by(phone=phone).first()
    if user is None:
        user = User(phone=phone)
        db.session.add(user)
    user.last_login_at = db.func.now()
    db.session.commit()
    token = create_jwt(user.id, phone)
    return api_response(True, data={"token": token, "user": {"id": user.id, "phone": user.phone, "name": user.name}})


@api_v1_bp.get("/me")
@auth_required
def me(auth_user_id: int):
    user = User.query.get(auth_user_id)
    if not user:
        return api_response(False, error={"message": "کاربر یافت نشد."}, status=404)
    return api_response(True, data={"id": user.id, "phone": user.phone, "name": user.name})


