from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional

from flask import current_app, request

from . import api_v1_bp
from .models import Ad, AdImage, Category, City
from ..extensions import db
from .utils import (
    ALLOWED_IMAGE_EXT,
    api_response,
    auth_required,
    file_url_for,
    get_auth_user_id,
    is_allowed_image,
    paginate_query,
)


def ad_to_dict(ad: Ad, with_images: bool = True) -> Dict:
    data = {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "price": ad.price,
        "area": ad.area,
        "is_active": ad.is_active,
        "city": {"id": ad.city_id, "name": ad.city.name if ad.city else None, "province": ad.city.province if ad.city else None},
        "category": {"id": ad.category_id, "name": ad.category.name if ad.category else None},
        "owner_id": ad.user_id,
        "created_at": ad.created_at.isoformat() if ad.created_at else None,
        "updated_at": ad.updated_at.isoformat() if ad.updated_at else None,
    }
    if with_images:
        data["images"] = [{"id": img.id, "url": img.file_url, "order": img.sort_order} for img in ad.images]
    return data


@api_v1_bp.get("/ads")
def list_ads():
    page = int(request.args.get("page", "1") or "1")
    page_size = int(request.args.get("page_size", "20") or "20")
    q = (request.args.get("q") or "").strip()
    city = (request.args.get("city") or "").strip()
    type_ = (request.args.get("type") or "").strip()
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    min_area = request.args.get("min_area")
    max_area = request.args.get("max_area")

    query = Ad.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Ad.title.ilike(like), Ad.description.ilike(like)))
    if city:
        # filter by city name or id
        if city.isdigit():
            query = query.filter(Ad.city_id == int(city))
        else:
            query = query.join(City, isouter=True).filter(City.name.ilike(f"%{city}%"))
    if type_:
        if type_.isdigit():
            query = query.filter(Ad.category_id == int(type_))
        else:
            query = query.join(Category, isouter=True).filter(Category.slug == type_)
    if min_price:
        try:
            query = query.filter(Ad.price >= int(min_price))
        except Exception:
            pass
    if max_price:
        try:
            query = query.filter(Ad.price <= int(max_price))
        except Exception:
            pass
    if min_area:
        try:
            query = query.filter(Ad.area >= int(min_area))
        except Exception:
            pass
    if max_area:
        try:
            query = query.filter(Ad.area <= int(max_area))
        except Exception:
            pass

    items, meta = paginate_query(query, page, page_size)
    return api_response(True, data=[ad_to_dict(a) for a in items], meta=meta)


@api_v1_bp.get("/ads/<int:ad_id>")
def get_ad(ad_id: int):
    ad = Ad.query.get(ad_id)
    if not ad or not ad.is_active:
        return api_response(False, error={"message": "آگهی یافت نشد."}, status=404)
    return api_response(True, data=ad_to_dict(ad))


@api_v1_bp.post("/ads")
@auth_required
def create_ad(auth_user_id: int):
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return api_response(False, error={"message": "عنوان الزامی است."}, status=400)
    ad = Ad(
        title=title,
        description=payload.get("description"),
        price=payload.get("price"),
        area=payload.get("area"),
        user_id=auth_user_id,
        city_id=payload.get("city_id"),
        category_id=payload.get("category_id"),
        is_active=True,
    )
    db.session.add(ad)
    db.session.commit()
    return api_response(True, data=ad_to_dict(ad), status=201)


@api_v1_bp.put("/ads/<int:ad_id>")
@auth_required
def update_ad(ad_id: int, auth_user_id: int):
    ad = Ad.query.get(ad_id)
    if not ad or ad.user_id != auth_user_id:
        return api_response(False, error={"message": "مجوز کافی وجود ندارد."}, status=403)
    payload = request.get_json(silent=True) or {}
    for key in ["title", "description"]:
        if key in payload:
            setattr(ad, key, (payload.get(key) or "").strip())
    for key in ["price", "area", "city_id", "category_id", "is_active"]:
        if key in payload:
            setattr(ad, key, payload.get(key))
    db.session.commit()
    return api_response(True, data=ad_to_dict(ad))


@api_v1_bp.delete("/ads/<int:ad_id>")
@auth_required
def delete_ad(ad_id: int, auth_user_id: int):
    ad = Ad.query.get(ad_id)
    if not ad or ad.user_id != auth_user_id:
        return api_response(False, error={"message": "مجوز کافی وجود ندارد."}, status=403)
    db.session.delete(ad)
    db.session.commit()
    return api_response(True, data={"deleted": True})


@api_v1_bp.post("/ads/<int:ad_id>/images")
@auth_required
def upload_ad_images(ad_id: int, auth_user_id: int):
    ad = Ad.query.get(ad_id)
    if not ad or ad.user_id != auth_user_id:
        return api_response(False, error={"message": "مجوز کافی وجود ندارد."}, status=403)
    if "images" not in request.files:
        return api_response(False, error={"message": "تصویری ارسال نشده است."}, status=400)
    files = request.files.getlist("images")
    saved: List[dict] = []
    uploads_root = current_app.config["UPLOAD_FOLDER"]
    ad_dir = os.path.join(uploads_root, "ads", str(ad_id))
    os.makedirs(ad_dir, exist_ok=True)
    # Determine current max order
    current_max = db.session.query(db.func.coalesce(db.func.max(AdImage.sort_order), 0)).filter(AdImage.ad_id == ad_id).scalar() or 0
    for f in files:
        filename = f.filename or ""
        if not is_allowed_image(filename):
            return api_response(False, error={"message": f"پسوند مجاز نیست. {ALLOWED_IMAGE_EXT}"} , status=400)
        ext = filename.rsplit(".", 1)[-1].lower()
        new_name = f"{uuid.uuid4().hex}.{ext}"
        path_abs = os.path.join(ad_dir, new_name)
        f.save(path_abs)
        url = file_url_for(path_abs)
        current_max += 1
        img = AdImage(ad_id=ad_id, file_url=url, sort_order=current_max)
        db.session.add(img)
        saved.append({"id": None, "url": url, "order": current_max})
    db.session.commit()
    # refresh ids
    imgs = AdImage.query.filter_by(ad_id=ad_id).order_by(AdImage.sort_order).all()
    return api_response(True, data=[{"id": im.id, "url": im.file_url, "order": im.sort_order} for im in imgs])


