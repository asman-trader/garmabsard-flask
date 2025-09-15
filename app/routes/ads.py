# app/routes/ads.py
# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from . import main_bp
from ..utils.storage import data_dir, load_ads, save_ads, load_settings
from ..utils.dates import parse_datetime_safe
from ..constants import CATEGORY_KEYS, CATEGORY_MAP

# ✅ سرویس اعلان‌ها
try:
    from app.services.notifications import add_notification
except Exception:
    # اگر سرویس اعلان هنوز اضافه نشده باشد، جلوی کرش را می‌گیریم.
    def add_notification(*args, **kwargs):
        return None


def _to_int(x, default=0):
    try:
        return int(str(x).replace(',', '').strip())
    except Exception:
        return default

def _safe_remove_file(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        # TODO: بهتر است لاگ شود
        pass


# ⚠️ قبلاً endpoint پیش‌فرض «submit_ad» باعث تداخل شده بود.
# با endpoint یکتا مشکل رفع می‌شود.
@main_bp.route('/submit-ad', methods=['GET', 'POST'], endpoint='submit_ad')
def submit_ad_redirect():
    return redirect(url_for('main.add_land_step1'))


@main_bp.route('/lands/add/step1', methods=['GET','POST'], endpoint='add_land_step1')
def add_land_step1():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land_step1')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        trade_type = (request.form.get('trade_type') or '').strip()  # sale|rent
        property_type = (request.form.get('property_type') or '').strip()  # apartment|villa|land|shop|office|garden
        if trade_type not in {'sale','rent'}:
            flash('نوع معامله نامعتبر است.')
            return redirect(url_for('main.add_land_step1'))
        if property_type not in {'apartment','villa','land','shop','office','garden'}:
            flash('نوع ملک نامعتبر است.')
            return redirect(url_for('main.add_land_step1'))
        session['ad_category'] = {
            'trade_type': trade_type,
            'property_type': property_type,
        }
        return redirect(url_for('main.add_land'))

    return render_template('add_land_step1.html')


@main_bp.route('/lands/add', methods=['GET','POST'], endpoint='add_land')
def add_land():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land')
        return redirect(url_for('main.login'))

    # Guard: اگر دسته انتخاب نشده باشد کاربر را به گام ۱ بفرست
    if request.method == 'GET':
        if not session.get('ad_category'):
            flash('لطفاً ابتدا دسته ملک را انتخاب کنید.')
            return redirect(url_for('main.add_land_step1'))
        # رندر گام ۲ جدید
        return render_template('add_land_step2.html', ad_category=session.get('ad_category'))

    if request.method == 'POST':
        # Step 2 (Basics): only images + title + description
        title = (request.form.get('title') or '').strip()
        description = request.form.get('description') or None

        # Server-side validation for lengths
        if len(title) > 60:
            flash("حداکثر طول عنوان ۶۰ کاراکتر است.")
            return redirect(url_for('main.add_land'))
        if description is not None and len(description) > 950:
            flash("حداکثر طول توضیحات ۹۵۰ کاراکتر است.")
            return redirect(url_for('main.add_land'))

        if not title or len(title) < 11:
            flash("عنوان باید بیش از ۱۰ و حداکثر ۶۰ کاراکتر باشد.")
            return redirect(url_for('main.add_land'))
        if description is None or len(description.strip()) < 51:
            flash("توضیحات باید بیش از ۵۰ و حداکثر ۹۵۰ کاراکتر باشد.")
            return redirect(url_for('main.add_land'))

        # Prefer uploaded_image_ids collected by client-side uploader
        uploaded_ids_raw = (request.form.get('uploaded_image_ids') or '').strip(', ')
        def _normalize_id(s: str) -> str:
            s = (s or '').strip()
            if s.startswith('/uploads/'):
                s = s[len('/uploads/'):]
            return s.lstrip('/')
        image_names = [ _normalize_id(x) for x in uploaded_ids_raw.split(',') if x.strip() ]

        if not image_names:
            # Backward compatibility: accept uploaded files if any
            tmp_code = datetime.now().strftime('%Y%m%d%H%M%S')
            upload_dir = os.path.join(data_dir(), 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            for img in request.files.getlist('images'):
                if img and img.filename:
                    fname = f"{tmp_code}__{secure_filename(img.filename)}"
                    img.save(os.path.join(upload_dir, fname))
                    image_names.append(fname)

        code = session.get('land_code') or datetime.now().strftime('%Y%m%d%H%M%S')
        lt = session.get('land_temp') or {}
        lt.update({'title': title, 'description': description})

        session.update({
            'land_code': code,
            'land_temp': lt,
            'land_images': image_names,
        })
        return redirect(url_for('main.add_land_details'))


@main_bp.route('/lands/add/step3', methods=['GET','POST'], endpoint='add_land_step3')
def add_land_step3():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land_step3')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        ad_type = request.form.get('ad_type')
        if ad_type not in ['site','broadcast']:
            flash("نوع آگهی نامعتبر است.")
            return redirect(url_for('main.add_land_step3'))
        session['land_ad_type'] = ad_type
        return redirect(url_for('main.finalize_land'))
    return render_template('add_land_step3.html')


# New: Step 3 (Details)
@main_bp.route('/lands/add/details', methods=['GET','POST'], endpoint='add_land_details')
def add_land_details():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land_details')
        return redirect(url_for('main.login'))

    if not session.get('land_temp'):
        return redirect(url_for('main.add_land'))

    if request.method == 'POST':
        price_total = request.form.get('price_total') or None
        size = request.form.get('size') or None
        location = request.form.get('location') or request.form.get('city') or None

        category = (request.form.get('category','') or '').strip()
        if category and category not in CATEGORY_KEYS:
            category = ""

        # Handle amenities from checkboxes
        amenities = request.form.getlist('amenities') or []
        conditions = request.form.getlist('conditions') or []
        
        extras = {
            'deposit': request.form.get('deposit') or None,
            'rent': request.form.get('rent') or None,
            'convertible': bool(request.form.get('convertible')),
            'year_built': request.form.get('year_built') or None,
            'floor': request.form.get('floor') or None,
            'rooms': request.form.get('rooms') or None,
            'bathrooms': request.form.get('bathrooms') or None,
            'elevator': 'elevator' in amenities,
            'parking': 'parking' in amenities,
            'warehouse': 'storage' in amenities,
            'balcony': 'balcony' in amenities,
            'yard': 'yard' in amenities,
            'pool': 'pool' in amenities,
            'frontage': request.form.get('frontage') or None,
            'length': request.form.get('length') or None,
            'street_width': request.form.get('street_width') or None,
            'is_negotiable': bool(request.form.get('is_negotiable')),
            'accept_exchange': 'exchange' in conditions,
            'installment': 'installment' in conditions,
            'urgent': 'immediate' in conditions,
            'features': request.form.getlist('features') or [],
            'document_type': request.form.get('document_type') or None,
            # Apartment
            'apartment': {
                'year_built': request.form.get('year_built') or None,
                'floor': request.form.get('floor') or None,
                'rooms': request.form.get('rooms') or None,
                'elevator': request.form.get('elevator') if request.form.get('elevator') in {'0','1'} else None,
                'parking': request.form.get('parking') if request.form.get('parking') in {'0','1'} else None,
                'warehouse': request.form.get('warehouse') if request.form.get('warehouse') in {'0','1'} else None,
            },
            # Villa
            'villa': {
                'land_area': request.form.get('villa_land_area') or None,
                'built_area': request.form.get('villa_built_area') or None,
                'bedrooms': request.form.get('villa_bedrooms') or None,
                'pool': request.form.get('villa_pool') if request.form.get('villa_pool') in {'0','1'} else None,
            },
            # Land / Garden
            'land': {
                'shape': request.form.get('land_shape') or None,
                'use': request.form.get('land_use') or None,
                'irrigation': request.form.get('irrigation') or None,
                'tree_count': request.form.get('tree_count') or None,
            },
            # Commercial
            'commercial': {
                'front_width': request.form.get('front_width') or None,
                'floor': request.form.get('commercial_floor') or None,
                'has_license': request.form.get('has_license') if request.form.get('has_license') in {'0','1'} else None,
                'type': request.form.get('commercial_type') or None,
            },
        }

        lt = session.get('land_temp') or {}
        lt.update({
            'location': location,
            'size': size,
            'price_total': _to_int(price_total) if price_total else None,
            'category': category or lt.get('category',''),
            'extras': extras,
        })
        session['land_temp'] = lt
        return redirect(url_for('main.add_land_step3'))

    return render_template('add_land_details.html', ad_category=session.get('ad_category'))


@main_bp.route('/lands/finalize', methods=['GET'], endpoint='finalize_land')
def finalize_land():
    keys = ['land_code','land_temp','land_images','land_ad_type']
    if not all(k in session for k in keys):
        flash("اطلاعات ناقص است.")
        return redirect(url_for('main.add_land'))

    settings = load_settings()
    status = 'approved' if settings.get('approval_method','manual') == 'auto' else 'pending'

    lands = load_ads()
    lt = session['land_temp']
    new_land = {
        'code': session['land_code'],
        'title': lt['title'],
        'location': lt['location'],
        'size': lt['size'],
        'price_total': lt['price_total'],
        'description': lt.get('description'),
        'images': session['land_images'],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'owner': session.get('user_phone'),
        'status': status,
        'ad_type': session['land_ad_type'],
        'category': lt.get('category',''),
        'extras': lt.get('extras', {})
    }
    lands.append(new_land)
    save_ads(lands)

    # ✅ اعلان سمت کاربر بعد از ذخیره آگهی
    try:
        user_id = session.get('user_phone')
        if user_id:
            if status == 'approved':
                # تأیید خودکار
                add_notification(
                    user_id=user_id,
                    title="آگهی شما تأیید و منتشر شد",
                    body="آگهی شما هم‌اکنون در وینور منتشر شده است.",
                    ntype="success",
                    ad_id=new_land['code'],
                    action_url=url_for('main.land_detail', code=new_land['code'])
                )
            else:
                # در انتظار تأیید
                add_notification(
                    user_id=user_id,
                    title="آگهی شما ثبت شد",
                    body="وضعیت: در انتظار تأیید. به‌محض بررسی، نتیجه اطلاع‌رسانی می‌شود.",
                    ntype="status",
                    ad_id=new_land['code'],
                    action_url=url_for('main.land_detail', code=new_land['code'])
                )
    except Exception:
        # سکوت در صورت نبود سرویس اعلان یا خطای غیرمنتظره
        pass

    # پاکسازی سشن مراحل
    for k in keys:
        session.pop(k, None)

    flash("✅ آگهی شما ثبت شد." + (" منتشر شد." if status=='approved' else " و منتظر تأیید است."))
    return redirect(url_for('main.my_lands'))


@main_bp.route('/my-lands', methods=['GET'], endpoint='my_lands')
def my_lands():
    if 'user_phone' not in session:
        flash("برای مشاهده وارد شوید.")
        session['next'] = url_for('main.my_lands')
        return redirect(url_for('main.login'))

    q        = (request.args.get('q') or '').strip().lower()
    status   = (request.args.get('status') or '').strip()
    sort     = (request.args.get('sort') or 'new').strip()
    page     = int(request.args.get('page', 1) or 1)
    per_page = min(int(request.args.get('per_page', 12) or 12), 48)

    lands_all = load_ads()
    user_lands = [l for l in lands_all if l.get('owner') == session['user_phone']]

    if status in {'approved','pending','rejected'}:
        user_lands = [l for l in user_lands if l.get('status') == status]

    if q:
        def _hit(ad):
            title = (ad.get('title') or '').lower()
            loc   = (ad.get('location') or '').lower()
            desc  = (ad.get('description') or '').lower()
            code  = str(ad.get('code') or '')
            return (q in title) or (q in loc) or (q in desc) or (q == code)
        user_lands = [ad for ad in user_lands if _hit(ad)]

    if sort == 'old':
        user_lands.sort(key=lambda x: parse_datetime_safe(x.get('created_at','1970-01-01')))
    elif sort == 'size_desc':
        user_lands.sort(key=lambda x: int(x.get('size') or 0), reverse=True)
    elif sort == 'size_asc':
        user_lands.sort(key=lambda x: int(x.get('size') or 0))
    else:
        user_lands.sort(key=lambda x: parse_datetime_safe(x.get('created_at','1970-01-01')), reverse=True)

    total = len(user_lands)
    pages = max((total - 1) // per_page + 1, 1)
    page  = max(min(page, pages), 1)
    items = user_lands[(page-1)*per_page : (page-1)*per_page + per_page]

    def page_url(p):
        args = request.args.to_dict()
        args['page'] = p
        return url_for('main.my_lands', **args)

    pagination = {
        'page': page, 'per_page': per_page, 'pages': pages, 'total': total,
        'has_prev': page > 1, 'has_next': page < pages
    }
    return render_template('my_lands.html', lands=items, pagination=pagination, page_url=page_url, CATEGORY_MAP=CATEGORY_MAP)


@main_bp.route('/lands/edit/<code>', methods=['GET','POST'], endpoint='edit_land')
def edit_land(code):
    if 'user_phone' not in session:
        flash("برای ویرایش وارد شوید.")
        session['next'] = url_for('main.edit_land', code=code)
        return redirect(url_for('main.login'))

    lands = load_ads()
    land = next((l for l in lands if l.get('code') == code and l.get('owner') == session['user_phone']), None)
    if not land:
        flash("آگهی پیدا نشد.")
        return redirect(url_for('main.my_lands'))

    if request.method == 'POST':
        category = (request.form.get('category','') or '').strip()
        if category and category not in CATEGORY_KEYS:
            category = land.get('category','')

        land.update({
            'title': request.form.get('title'),
            'location': request.form.get('location'),
            'size': request.form.get('size'),
            'price_total': _to_int(request.form.get('price_total')) if request.form.get('price_total') else None,
            'description': request.form.get('description'),
            'category': category
        })

        folder = os.path.join(data_dir(), 'uploads')
        os.makedirs(folder, exist_ok=True)
        saved = []
        for img in request.files.getlist('images'):
            if img and img.filename:
                fname = f"{code}__{secure_filename(img.filename)}"
                img.save(os.path.join(folder, fname))
                saved.append(fname)
        if saved:
            land['images'] = saved

        save_ads(lands)
        flash("✅ آگهی ویرایش شد.")
        return redirect(url_for('main.my_lands'))

    return render_template('edit_land.html', land=land, CATEGORY_MAP=CATEGORY_MAP)


@main_bp.route('/lands/delete/<code>', methods=['POST'], endpoint='delete_land')
def delete_land(code):
    if 'user_phone' not in session:
        flash("برای حذف وارد شوید.")
        return redirect(url_for('main.login'))

    lands = load_ads()
    target = next((l for l in lands if l.get('code') == code and l.get('owner') == session['user_phone']), None)
    if not target:
        flash("❌ آگهی پیدا نشد یا متعلق به شما نیست.")
        return redirect(url_for('main.my_lands'))

    # حذف فایل‌های تصویر (در صورت وجود)
    upload_dir = os.path.join(data_dir(), 'uploads')
    for fname in (target.get('images') or []):
        _safe_remove_file(os.path.join(upload_dir, fname))

    # حذف رکورد
    new_lands = [l for l in lands if l is not target]
    save_ads(new_lands)
    flash("🗑️ آگهی حذف شد.")
    return redirect(url_for('main.my_lands'))


## consult endpoint removed


# حذف آگهی با مسیر دوم (سازگار با فرم‌های جدید)
@main_bp.route('/ads/<code>/delete', methods=['POST'], endpoint='ad_delete')
def ad_delete(code):
    if 'user_phone' not in session:
        flash("برای حذف وارد شوید.", "warning")
        return redirect(url_for('main.login'))

    lands = load_ads()
    target = next((l for l in lands if l.get('code') == code and l.get('owner') == session['user_phone']), None)
    if not target:
        flash("❌ آگهی پیدا نشد یا متعلق به شما نیست.", "danger")
        return redirect(url_for('main.my_lands'))

    # حذف فایل‌های تصویر (اختیاری)
    upload_dir = os.path.join(data_dir(), 'uploads')
    for fname in (target.get('images') or []):
        _safe_remove_file(os.path.join(upload_dir, fname))

    # حذف رکورد
    new_lands = [l for l in lands if l is not target]
    save_ads(new_lands)
    flash('🗑️ آگهی با موفقیت حذف شد.', 'success')
    return redirect(url_for('main.my_lands'))
