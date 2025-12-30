from __future__ import annotations

from flask import request

from . import api_v1_bp
from .models import Ad, Consultation
from ..extensions import db
from .utils import api_response


@api_v1_bp.post("/consultations")
def create_consultation():
    payload = request.get_json(silent=True) or {}
    ad_id = payload.get("ad_id")
    phone = (payload.get("phone") or "").strip()
    message = (payload.get("message") or "").strip()
    if not phone:
        return api_response(False, error={"message": "شماره تماس الزامی است."}, status=400)
    if ad_id:
        ad = Ad.query.get(ad_id)
        if not ad:
            return api_response(False, error={"message": "آگهی یافت نشد."}, status=404)
    c = Consultation(ad_id=ad_id, phone=phone, message=message)
    db.session.add(c)
    db.session.commit()
    return api_response(True, data={"id": c.id})


