# app/routes/lands.py
# -*- coding: utf-8 -*-
"""
Vinor (vinor.ir) – Lands Routes (Final)
- Mobile-first، امن و شفاف
- افزودن آگهی (GET/POST) با دیباگ درست و جلوگیری از کش فرم (no-store)
- ذخیره آگهی‌ها در app/data/lands.json (یا از app.config['LANDS_FILE'] اگر تعریف شده)
- آپلود تصاویر به app/data/uploads/lands
- نمایش جزئیات آگهی
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

from flask import (
    Blueprint, render_template, request, current_app,
    redirect, url_for, make_response, abort
)
from werkzeug.datastructures import MultiDict
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound

lands_bp = Blueprint("lands", __name__)

# اگر WTForms داری:
try:
    from .forms import LandForm  # باید فیلد csrf را داشته باشد
except Exception:
    LandForm = None


# ----------------------------- Helpers -----------------------------
def _lands_file_path() -> str:
    """مسیر فایل lands.json: اولویت با app.config['LANDS_FILE']؛
    در غیر اینصورت app/data/lands.json"""
    cfg_path = current_app.config.get("LANDS_FILE")
    if cfg_path:
        return cfg_path
    return os.path.join(current_app.root_path, "data", "lands.json")


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _load_lands() -> List[Dict[str, Any]]:
    path = _lands_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        current_app.logger.warning("LOAD_LANDS_FAILED: %s", e)
        return []


def _save_lands(items: List[Dict[str, Any]]) -> None:
    path = _lands_file_path()
    _ensure_parent_dir(path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _uploads_dir() -> str:
    """پوشه آپلود تصاویر آگهی‌ها: app/data/uploads/lands"""
    base = current_app.config.get("UPLOAD_FOLDER") or os.path.join(current_app.root_path, "data", "uploads")
    p = os.path.join(base, "lands")
    os.makedirs(p, exist_ok=True)
    return p


ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _save_images(files) -> List[str]:
    """ذخیره تصاویر ورودی؛ خروجی: لیست نام‌فایل‌های ذخیره‌شده (نسبت به /uploads)"""
    saved = []
    if not files:
        return saved
    dest = _uploads_dir()
    for fs in files.getlist("images"):  # نام input: images[]
        if not fs or not getattr(fs, "filename", ""):
            continue
        filename = secure_filename(fs.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            current_app.logger.info("SKIP_FILE_EXT: %s", filename)
            continue
        newname = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(dest, newname)
        fs.save(path)
        # مسیر وب: اگر بلوپرینت uploads مسیر /uploads را سرو می‌کند، مطابق آن بساز
        saved.append(f"/uploads/lands/{newname}")
    return saved


def _required_fields_ok(form: MultiDict) -> (bool, List[str]):
    """ولیدیشن ساده برای حالت بدون WTForms"""
    required = ["title", "area"]  # حداقل‌ها
    missing = [k for k in required if not (form.get(k) or "").strip()]
    return (len(missing) == 0), missing


def _build_land_record(form: MultiDict, images: List[str]) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    # فیلدهای پایه؛ در صورت نیاز می‌توانی توسعه دهی (price, location, description, owner_phone, ...)
    return {
        "id": uuid.uuid4().hex,
        "title": (form.get("title") or "").strip(),
        "area": (form.get("area") or "").strip(),
        "price": (form.get("price") or "").strip(),
        "location": (form.get("location") or "").strip(),
        "description": (form.get("description") or "").strip(),
        "images": images,
        "created_at": now,
        "updated_at": now,
        "status": "pending",  # در صورت وجود approval_method می‌توان auto کرد
        "brand": "Vinor",
    }


# ----------------------------- Routes -----------------------------
@lands_bp.route("/submit-ad")
def submit_ad_redirect():
    """سازگاری با لینک‌های قدیمی: /submit-ad → /lands/add"""
    return redirect(url_for("lands.add_land"))


@lands_bp.route("/lands/add", methods=["GET", "POST"])
def add_land():
    """
    - GET: فرم با Cache-Control: no-store (توکن CSRF کهنه نشود)
    - POST: اگر خطا → 400 + لاگ؛ اگر موفق → ذخیره و ریدایرکت به جزئیات
    """
    # --- GET ---
    if request.method == "GET":
        form = LandForm() if LandForm else None
        resp = make_response(render_template("lands/add.html", form=form))
        resp.headers["Cache-Control"] = "no-store"
        return resp

    # --- POST ---
    form_data = request.form if request.form else MultiDict()
    file_data = request.files if request.files else MultiDict()

    current_app.logger.info("ADD_POST_HIT: path=%s", request.path)
    current_app.logger.info("ADD_POST_FORM: %s", dict(form_data))
    current_app.logger.info("ADD_POST_FILES: %s", list(file_data.keys()))

    # مسیر WTForms (اگر موجود باشد)
    if LandForm:
        form = LandForm()
        try:
            valid = form.validate_on_submit()  # شامل CSRF، اگر Flask-WTF فعال باشد
        except Exception as e:
            current_app.logger.exception("FORM_VALIDATE_EXCEPTION: %s", e)
            return render_template("lands/add.html", form=form), 400

        if not valid:
            current_app.logger.info("ADD_FORM_ERRORS: %s", getattr(form, "errors", {}))
            return render_template("lands/add.html", form=form), 400

        # آپلود تصاویر
        saved_images = _save_images(file_data)

        # ساخت رکورد و ذخیره
        items = _load_lands()
        record = _build_land_record(form_data, saved_images)
        items.append(record)
        _save_lands(items)

        current_app.logger.info("ADD_OK -> redirect detail id=%s", record["id"])
        return redirect(url_for("lands.land_detail", id=record["id"]))

    # مسیر بدون WTForms (فرم دستی + CSRFProtect)
    ok, missing = _required_fields_ok(form_data)
    if not ok:
        current_app.logger.info("ADD_MISSING_FIELDS: %s", missing)
        # بارگذاری مجدد فرم با کد 400
        return render_template("lands/add.html", form=None), 400

    saved_images = _save_images(file_data)
    items = _load_lands()
    record = _build_land_record(form_data, saved_images)
    items.append(record)
    _save_lands(items)

    current_app.logger.info("ADD_OK (no-WTForms) -> redirect id=%s", record["id"])
    return redirect(url_for("lands.land_detail", id=record["id"]))


@lands_bp.route("/lands/<id>")
def land_detail(id):
    """نمایش جزئیات آگهی"""
    items = _load_lands()
    data = next((x for x in items if str(x.get("id")) == str(id)), None)
    if not data:
        abort(404)

    # اگر تمپلیت داشتی، همونو رندر کن؛ اگر نبود، خروجی ساده
    try:
        return render_template("lands/detail.html", land=data)
    except TemplateNotFound:
        # خروجی fallback ساده (برای تست سریع)
        lines = [
            f"Vinor – Land Detail",
            f"id: {data.get('id')}",
            f"title: {data.get('title')}",
            f"area: {data.get('area')}",
            f"price: {data.get('price')}",
            f"images: {', '.join(data.get('images') or [])}",
            f"status: {data.get('status')}",
        ]
        return "\n".join(lines), 200
