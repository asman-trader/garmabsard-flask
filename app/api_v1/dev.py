from __future__ import annotations

from flask import current_app

from . import api_v1_bp
from .models import Ad, AdImage, Category, City, User
from ..extensions import db
from .utils import api_response


@api_v1_bp.post("/dev/seed")
def seed_data():
    if current_app.env == "production":
        return api_response(False, error={"message": "forbidden"}, status=403)
    # Basic seed if empty
    if not Category.query.first():
        c1 = Category(name="زمین", slug="land")
        c2 = Category(name="ویلا", slug="villa")
        c3 = Category(name="آپارتمان", slug="apartment")
        db.session.add_all([c1, c2, c3])
    if not City.query.first():
        tehran = City(name="تهران", province="تهران")
        karaj = City(name="کرج", province="البرز")
        shiraz = City(name="شیراز", province="فارس")
        db.session.add_all([tehran, karaj, shiraz])
    if not User.query.first():
        u = User(phone="09120000000", name="کاربر نمونه")
        db.session.add(u)
        db.session.flush()
        # Ads
        a1 = Ad(title="زمین ۵۰۰ متری خوش‌قواره", description="سند تک‌برگ، دسترسی عالی", price=1500000000, area=500, user_id=u.id, city_id=1, category_id=1, is_active=True)
        a2 = Ad(title="ویلا دوبلکس شهرکی", description="نوساز، فول امکانات", price=8500000000, area=300, user_id=u.id, city_id=2, category_id=2, is_active=True)
        a3 = Ad(title="آپارتمان ۸۵ متری", description="طبقه ۳ با آسانسور", price=3200000000, area=85, user_id=u.id, city_id=1, category_id=3, is_active=True)
        db.session.add_all([a1, a2, a3])
    db.session.commit()
    return api_response(True, data={"seeded": True})


