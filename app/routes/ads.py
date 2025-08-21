# app/routes/ads.py
import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from . import main_bp
from ..utils.storage import data_dir, load_ads, save_ads, load_consults, save_consults, load_settings
from ..utils.dates import parse_datetime_safe
from ..constants import CATEGORY_KEYS, CATEGORY_MAP

def _to_int(x, default=0):
    try: return int(str(x).replace(',', '').strip())
    except Exception: return default

@main_bp.route('/submit-ad', methods=['GET','POST'])
def submit_ad():
    return redirect(url_for('main.add_land'))

@main_bp.route('/lands/add', methods=['GET','POST'])
def add_land():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land')
        return redirect(url_for('main.send_otp'))

    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        size = request.form.get('size')
        price_total = request.form.get('price_total') or None
        description = request.form.get('description')
        category = (request.form.get('category','') or '').strip()
        if category and category not in CATEGORY_KEYS:
            category = ""

        if not title or not location or not size:
            flash("همه فیلدها الزامی هستند.")
            return redirect(url_for('main.add_land'))

        code = datetime.now().strftime('%Y%m%d%H%M%S')
        upload_dir = os.path.join(data_dir(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        image_names = []
        for img in request.files.getlist('images'):
            if img and img.filename:
                fname = f"{code}__{secure_filename(img.filename)}"
                img.save(os.path.join(upload_dir, fname))
                image_names.append(fname)

        session.update({
            'land_code': code,
            'land_temp': {
                'title': title, 'location': location, 'size': size,
                'price_total': _to_int(price_total) if price_total else None,
                'description': description, 'category': category
            },
            'land_images': image_names
        })
        return redirect(url_for('main.add_land_step3'))

    return render_template('add_land.html', CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route('/lands/add/step3', methods=['GET','POST'])
def add_land_step3():
    if 'user_phone' not in session:
        flash("برای ثبت آگهی وارد شوید.")
        session['next'] = url_for('main.add_land_step3')
        return redirect(url_for('main.send_otp'))
    if request.method == 'POST':
        ad_type = request.form.get('ad_type')
        if ad_type not in ['site','broadcast']:
            flash("نوع آگهی نامعتبر است.")
            return redirect(url_for('main.add_land_step3'))
        session['land_ad_type'] = ad_type
        return redirect(url_for('main.finalize_land'))
    return render_template('add_land_step3.html')

@main_bp.route('/lands/finalize')
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
        'category': lt.get('category','')
    }
    lands.append(new_land)
    save_ads(lands)
    for k in keys: session.pop(k, None)

    flash("✅ آگهی شما ثبت شد." + (" منتشر شد." if status=='approved' else " و منتظر تأیید است."))
    return redirect(url_for('main.my_lands'))

@main_bp.route('/my-lands')
def my_lands():
    if 'user_phone' not in session:
        flash("برای مشاهده وارد شوید.")
        session['next'] = url_for('main.my_lands')
        return redirect(url_for('main.send_otp'))

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

@main_bp.route('/lands/edit/<code>', methods=['GET','POST'])
def edit_land(code):
    if 'user_phone' not in session:
        flash("برای ویرایش وارد شوید.")
        session['next'] = url_for('main.edit_land', code=code)
        return redirect(url_for('main.send_otp'))

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

@main_bp.route('/lands/delete/<code>', methods=['POST'])
def delete_land(code):
    if 'user_phone' not in session:
        flash("برای حذف وارد شوید.")
        return redirect(url_for('main.send_otp'))

    lands = load_ads()
    new_lands = [l for l in lands if not (l.get('code') == code and l.get('owner') == session['user_phone'])]
    if len(new_lands) == len(lands):
        flash("❌ آگهی پیدا نشد یا متعلق به شما نیست.")
    else:
        save_ads(new_lands)
        flash("🗑️ آگهی حذف شد.")
    return redirect(url_for('main.my_lands'))

@main_bp.route('/consult/<code>', methods=['POST'])
def consult(code):
    consults = load_consults()
    consults.append({
        'name': request.form.get('name'),
        'phone': request.form.get('phone'),
        'message': request.form.get('message'),
        'code': code,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_consults(consults)
    flash("✅ درخواست مشاوره ثبت شد.")
    return redirect(url_for('main.land_detail', code=code))
