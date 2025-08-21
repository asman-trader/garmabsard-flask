# app/routes/public.py
import os
from flask import render_template, send_from_directory, request
from . import main_bp
from ..utils.storage import data_dir, legacy_dir, load_ads
from ..utils.dates import parse_datetime_safe
from ..constants import CATEGORY_MAP

@main_bp.route("/")
def index():
    approved = [l for l in load_ads() if l.get('status') == 'approved']
    lands = sorted(approved, key=lambda x: parse_datetime_safe(x.get('created_at','1970-01-01')), reverse=True)
    return render_template("index.html", lands=lands, CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route("/land/<code>")
def land_detail(code):
    land = next((l for l in load_ads() if l.get('code') == code), None)
    if not land: return ("زمین پیدا نشد", 404)
    return render_template("land_detail.html", land=land, CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    for folder in (os.path.join(data_dir(),'uploads'), os.path.join(legacy_dir(),'uploads')):
        fp = os.path.join(folder, filename)
        if os.path.exists(fp):
            return send_from_directory(folder, filename)
    return ("File not found", 404)

@main_bp.route("/search")
def search_page():
    active_category = (request.args.get('category') or '').strip()
    if active_category not in CATEGORY_MAP: active_category = ""
    ads = [ad for ad in load_ads() if ad.get('status') == 'approved']
    if active_category:
        ads = [ad for ad in ads if ad.get('category','') == active_category]
    ads = sorted(ads, key=lambda x: parse_datetime_safe(x.get('created_at','1970-01-01')), reverse=True)
    return render_template("search.html", ads=ads, category=active_category, CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route("/search-results")
def search_results():
    q = (request.args.get('q','') or '').strip().lower()
    pool = [ad for ad in load_ads() if ad.get('status') == 'approved']
    results = []
    for ad in pool:
        title = (ad.get('title') or '').lower()
        loc   = (ad.get('location') or '').lower()
        desc  = (ad.get('description') or '').lower()
        if q and (q in title or q in loc or q in desc):
            results.append(ad)
    results = sorted(results, key=lambda x: parse_datetime_safe(x.get('created_at','1970-01-01')), reverse=True)
    return render_template("search_results.html", results=results, query=q, CATEGORY_MAP=CATEGORY_MAP)

@main_bp.route("/city")
def city_select():
    return render_template("city_select.html")
