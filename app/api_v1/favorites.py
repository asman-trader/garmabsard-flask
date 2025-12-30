from __future__ import annotations

from flask import request

from . import api_v1_bp
from .models import Ad, Favorite
from ..extensions import db
from .utils import api_response, auth_required


@api_v1_bp.get("/favorites")
@auth_required
def list_favorites(auth_user_id: int):
    favs = Favorite.query.filter_by(user_id=auth_user_id).all()
    data = [{"ad_id": f.ad_id, "id": f.id} for f in favs]
    return api_response(True, data=data)


@api_v1_bp.post("/favorites/<int:ad_id>")
@auth_required
def add_favorite(ad_id: int, auth_user_id: int):
    ad = Ad.query.get(ad_id)
    if not ad:
        return api_response(False, error={"message": "آگهی یافت نشد."}, status=404)
    exists = Favorite.query.filter_by(user_id=auth_user_id, ad_id=ad_id).first()
    if exists:
        return api_response(True, data={"id": exists.id, "ad_id": ad_id})
    fav = Favorite(user_id=auth_user_id, ad_id=ad_id)
    db.session.add(fav)
    db.session.commit()
    return api_response(True, data={"id": fav.id, "ad_id": ad_id}, status=201)


@api_v1_bp.delete("/favorites/<int:ad_id>")
@auth_required
def remove_favorite(ad_id: int, auth_user_id: int):
    fav = Favorite.query.filter_by(user_id=auth_user_id, ad_id=ad_id).first()
    if not fav:
        return api_response(True, data={"deleted": False})
    db.session.delete(fav)
    db.session.commit()
    return api_response(True, data={"deleted": True})


