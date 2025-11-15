from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from flask import (
    render_template, request, redirect, url_for, session,
    send_from_directory, current_app, abort, flash
)
import random, re

from . import express_partner_bp
from ..utils.storage import (
    load_express_partner_apps, save_express_partner_apps,
    load_express_partners, load_partner_notes, save_partner_notes,
    load_partner_sales, save_partner_sales,
    load_partner_files_meta, save_partner_files_meta,
    load_express_assignments, save_express_assignments, load_express_commissions,
    load_ads_cached,
)
from ..utils.share_tokens import encode_partner_ref
from ..services.notifications import get_user_notifications, unread_count, mark_read, mark_all_read
from flask import jsonify


def _sort_by_created_at_desc(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from ..utils.dates import parse_datetime_safe
    return sorted(items, key=lambda x: parse_datetime_safe(x.get('created_at', '1970-01-01')), reverse=True)


def _normalize_phone(phone: str) -> str:
    p = (phone or "").strip()
    p = re.sub(r"\D+", "", p)
    if p.startswith("0098"): p = "0" + p[4:]
    elif p.startswith("98"): p = "0" + p[2:]
    if not p.startswith("0"): p = "0" + p
    return p[:11]


def _get_my_last_application(phone: str) -> Dict[str, Any] | None:
    """Return latest Express Partner application for a phone, if any."""
    try:
        apps = load_express_partner_apps() or []
        mine = [a for a in apps if isinstance(a, dict) and str(a.get('phone')) == str(phone)]
        if not mine:
            return None
        try:
            mine.sort(key=lambda x: x.get('created_at',''), reverse=True)
        except Exception:
            pass
        return mine[0]
    except Exception:
        return None


def _has_active_application(phone: str) -> bool:
    """Return True if the user already has an in-progress application (not approved/rejected/cancelled)."""
    try:
        apps = load_express_partner_apps() or []
        active_statuses = {None, '', 'new', 'pending', 'under_review'}
        for a in apps:
            if not isinstance(a, dict):
                continue
            if str(a.get('phone')) != str(phone):
                continue
            status = str(a.get('status') or '').strip().lower()
            if status in ('approved', 'rejected', 'cancelled'):
                continue
            # anything else counts as active/in-progress
            return True
    except Exception:
        pass
    return False


@express_partner_bp.app_context_processor
def inject_role_flags():
    try:
        me = str(session.get("user_phone") or "").strip()
    except Exception:
        me = ""
    try:
        partners = load_express_partners() or []
        is_express_partner = any(
            isinstance(p, dict)
            and str(p.get("phone") or "").strip() == me
            and (str(p.get("status") or "").lower() == "approved" or p.get("status") is True)
            for p in partners
        )
    except Exception:
        is_express_partner = False
    return {
        "VINOR_IS_EXPRESS_PARTNER": is_express_partner,
    }


# -------------------------
# PWA Routes (Separate from main VINOR PWA)
# -------------------------
@express_partner_bp.route('/manifest.webmanifest', methods=['GET'], endpoint='manifest')
def serve_manifest():
    """Serve Express Partner manifest separately"""
    from flask import Response, send_from_directory
    import os
    static_dir = os.path.join(current_app.root_path, "static")
    file_path = os.path.join(static_dir, "express-partner.webmanifest")
    mimetype = "application/manifest+json"
    
    if os.path.exists(file_path):
        return send_from_directory(static_dir, "express-partner.webmanifest", mimetype=mimetype)
    
    # Fallback JSON
    fallback_json = '''{
      "id": "/express/partner/",
      "name": "وینور اکسپرس - پنل همکاران",
      "short_name": "وینور اکسپرس",
      "description": "پنل مدیریت همکاران وینور - دسترسی به آگهی‌های تخصیص یافته، کمیسیون‌ها و ابزارهای مدیریت",
      "dir": "rtl",
      "lang": "fa",
      "start_url": "/express/partner/dashboard?source=pwa",
      "scope": "/express/partner/",
      "display": "standalone",
      "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
      "orientation": "portrait",
      "background_color": "#7c3aed",
      "theme_color": "#7c3aed",
      "categories": ["business", "productivity"],
      "capture_links": "existing-client-navigate",
      "launch_handler": { "client_mode": "auto" },
      "icons": [
        { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable" },
        { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
      ]
    }'''
    return Response(fallback_json, status=200, mimetype=mimetype)


@express_partner_bp.route('/sw.js', methods=['GET'], endpoint='service_worker')
def serve_service_worker():
    """Serve Express Partner service worker separately"""
    from flask import send_from_directory
    import os
    static_dir = os.path.join(current_app.root_path, "static")
    return send_from_directory(static_dir, "express-partner-sw.js", mimetype="application/javascript")


@express_partner_bp.route('/offline', methods=['GET'], endpoint='offline')
def offline_page():
    """Express Partner offline page"""
    return render_template('express_partner/offline.html')


@express_partner_bp.route('/apply', methods=['GET'], endpoint='apply')
def apply():
    """Backward-compatible: redirect to step1 of multi-step flow"""
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.apply")))
    me_phone = (session.get("user_phone") or "").strip()
    # اگر قبلاً درخواست ثبت شده، کاربر را به صفحه تشکر ببر
    last_app = _get_my_last_application(me_phone)
    if last_app:
        return render_template('express_partner/thanks.html', name=(last_app.get('name') or ''))
    return redirect(url_for('express_partner.apply_step1'))


@express_partner_bp.route('/apply/step1', methods=['GET', 'POST'], endpoint='apply_step1')
def apply_step1():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.apply_step1")))
    me_phone = (session.get("user_phone") or "").strip()
    # اگر قبلاً درخواست ثبت شده، کاربر را به صفحه تشکر ببر
    last_app = _get_my_last_application(me_phone)
    if last_app:
        return render_template('express_partner/thanks.html', name=(last_app.get('name') or ''))
    # اگر قبلاً همکار است، به داشبورد برود
    try:
        partners = load_express_partners() or []
        if any(str(p.get('phone')) == me_phone for p in partners if isinstance(p, dict)):
            return redirect(url_for('express_partner.dashboard'))
    except Exception:
        pass

    if request.method == 'POST':
        # جلوگیری از ایجاد درخواست موازی
        if _has_active_application(me_phone):
            last_app = _get_my_last_application(me_phone)
            return render_template('express_partner/thanks.html', name=(last_app.get('name') if last_app else ''))
        name = (request.form.get('name') or '').strip()
        city = (request.form.get('city') or '').strip()
        if not name or not city:
            flash('نام و شهر الزامی است.', 'error')
            return render_template('express_partner/apply_step1.html', name=name, city=city)
        session['apply_data'] = {**(session.get('apply_data') or {}), 'name': name, 'city': city}
        return redirect(url_for('express_partner.apply_step2'))

    data = session.get('apply_data') or {}
    return render_template('express_partner/apply_step1.html', name=data.get('name',''), city=data.get('city',''))


@express_partner_bp.route('/apply/step2', methods=['GET', 'POST'], endpoint='apply_step2')
def apply_step2():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.apply_step2")))
    me_phone = (session.get("user_phone") or "").strip()
    # اگر قبلاً درخواست ثبت شده، کاربر را به صفحه تشکر ببر
    last_app = _get_my_last_application(me_phone)
    if last_app:
        return render_template('express_partner/thanks.html', name=(last_app.get('name') or ''))
    # اطمینان از تکمیل step1
    if not (session.get('apply_data') and session['apply_data'].get('name') and session['apply_data'].get('city')):
        return redirect(url_for('express_partner.apply_step1'))

    if request.method == 'POST':
        # جلوگیری از ایجاد درخواست موازی
        me_phone = (session.get('user_phone') or '').strip()
        if _has_active_application(me_phone):
            last_app = _get_my_last_application(me_phone)
            return render_template('express_partner/thanks.html', name=(last_app.get('name') if last_app else ''))
        experience = (request.form.get('experience') or '').strip()
        note = (request.form.get('note') or '').strip()
        session['apply_data'] = {**(session.get('apply_data') or {}), 'experience': experience, 'note': note}
        return redirect(url_for('express_partner.apply_step3'))

    data = session.get('apply_data') or {}
    return render_template('express_partner/apply_step2.html', experience=data.get('experience',''), note=data.get('note',''))


@express_partner_bp.route('/apply/step3', methods=['GET', 'POST'], endpoint='apply_step3')
def apply_step3():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.apply_step3")))
    me_phone = (session.get("user_phone") or "").strip()
    data = session.get('apply_data') or {}
    # اگر قبلاً درخواست ثبت شده، کاربر را به صفحه تشکر ببر
    last_app = _get_my_last_application(me_phone)
    if last_app and request.method == 'GET':
        return render_template('express_partner/thanks.html', name=(last_app.get('name') or ''))
    if not (data.get('name') and data.get('city')):
        return redirect(url_for('express_partner.apply_step1'))

    if request.method == 'POST':
        # اگر قبلاً درخواست فعال دارد، به صفحه تشکر هدایت شود
        if _has_active_application(me_phone):
            last_app = _get_my_last_application(me_phone)
            session.pop('apply_data', None)
            return render_template('express_partner/thanks.html', name=(last_app.get('name') if last_app else ''))
        # ذخیره نهایی
        apps = load_express_partner_apps() or []
        partners = load_express_partners() or []
        if any(str(p.get("phone")) == me_phone for p in partners if isinstance(p, dict)):
            session.pop('apply_data', None)
            return redirect(url_for("express_partner.dashboard"))

        new_id = (max([int(x.get("id", 0) or 0) for x in apps if isinstance(x, dict)], default=0) or 0) + 1
        record = {
            "id": new_id,
            "name": data.get('name',''),
            "phone": me_phone,
            "city": data.get('city',''),
            "experience": data.get('experience',''),
            "note": data.get('note',''),
            "status": "new",
            "created_at": datetime.utcnow().isoformat()+"Z",
        }
        apps.append(record)
        save_express_partner_apps(apps)
        session.pop('apply_data', None)
        return render_template("express_partner/thanks.html", name=record.get('name',''), brand="وینور", domain="vinor.ir")

    return render_template('express_partner/apply_step3.html', data=data)


@express_partner_bp.route('/dashboard', methods=['GET'], endpoint='dashboard')
def dashboard():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))

    me_phone = (session.get("user_phone") or "").strip()
    partners = load_express_partners() or []
    profile = next((p for p in partners if str(p.get("phone")) == me_phone), None)

    apps = load_express_partner_apps() or []
    my_apps = [a for a in apps if str(a.get("phone")) == me_phone]

    notes = [n for n in (load_partner_notes() or []) if str(n.get('phone')) == me_phone]
    sales = [s for s in (load_partner_sales() or []) if str(s.get('phone')) == me_phone]
    files = [f for f in (load_partner_files_meta() or []) if str(f.get('phone')) == me_phone]

    try:
        assignments = load_express_assignments() or []
    except Exception:
        assignments = []
    my_assignments = [a for a in assignments if str(a.get('partner_phone')) == me_phone and a.get('status') in (None,'active','pending','approved','in_transaction')]
    lands_all = load_ads_cached() or []
    code_to_land = {str(l.get('code')): l for l in lands_all}
    assigned_lands = []
    for a in my_assignments:
        land = code_to_land.get(str(a.get('land_code')))
        if not land:
            continue
        item = dict(land)
        item['_assignment_id'] = a.get('id')
        item['_assignment_status'] = a.get('status','active')
        item['_commission_pct'] = a.get('commission_pct')
        # محاسبه مبلغ پورسانت همکار از روی price_total (اگر موجود) و درصد کمیسیون
        try:
            total_price_str = str(item.get('price_total') or item.get('price') or '0').replace(',', '').strip()
            total_price = int(total_price_str) if total_price_str else 0
        except Exception:
            total_price = 0
        try:
            pct = float(item.get('_commission_pct') or 0)
        except Exception:
            pct = 0.0
        item['_commission_amount'] = int(round(total_price * (pct / 100.0))) if (total_price and pct) else 0
        share_token = encode_partner_ref(me_phone)
        try:
            item['_share_url'] = url_for('main.express_detail', code=item.get('code'), ref=share_token, _external=True)
        except Exception:
            item['_share_url'] = ''
        item['_share_token'] = share_token
        assigned_lands.append(item)

    try:
        comms = load_express_commissions() or []
        my_comms = [c for c in comms if str(c.get('partner_phone')) == me_phone]
    except Exception:
        my_comms = []
    total_commission = sum(int(c.get('commission_amount') or 0) for c in my_comms)
    pending_commission = sum(int(c.get('commission_amount') or 0) for c in my_comms if (c.get('status') or 'pending') == 'pending')
    sold_count = sum(1 for c in my_comms if (c.get('status') or '') in ('approved','paid'))

    is_approved = bool(profile and (profile.get("status") in ("approved", True)))
    return render_template(
        "express_partner/dashboard.html",
        profile=profile,
        is_approved=is_approved,
        my_apps=my_apps,
        notes=notes,
        sales=sales,
        files=files,
        assigned_lands=assigned_lands,
        total_commission=total_commission,
        pending_commission=pending_commission,
        sold_count=sold_count,
        hide_header=True,
        SHOW_SUBMIT_BUTTON=False,
        brand="وینور",
        domain="vinor.ir",
    )


@express_partner_bp.get('/notes', endpoint='notes')
def notes_page():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.notes")))
    me_phone = (session.get("user_phone") or "").strip()
    items = [n for n in (load_partner_notes() or []) if str(n.get('phone')) == me_phone]
    return render_template("express_partner/notes.html", notes=items, hide_header=True, SHOW_SUBMIT_BUTTON=False, brand="وینور", domain="vinor.ir")


@express_partner_bp.get('/commissions', endpoint='commissions')
def commissions_page():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.commissions")))
    me_phone = (session.get("user_phone") or "").strip()
    try:
        comms = load_express_commissions() or []
        my_comms = [c for c in comms if str(c.get('partner_phone')) == me_phone]
    except Exception:
        my_comms = []

    def _i(v):
        try:
            return int(str(v).replace(',', '').strip() or '0')
        except Exception:
            return 0

    total_commission = sum(_i(c.get('commission_amount')) for c in my_comms)
    pending_commission = sum(_i(c.get('commission_amount')) for c in my_comms if (c.get('status') or 'pending') == 'pending')
    paid_commission = sum(_i(c.get('commission_amount')) for c in my_comms if (c.get('status') or '') == 'paid')
    sold_count = sum(1 for c in my_comms if (c.get('status') or '') in ('approved','paid'))
    try:
        my_comms.sort(key=lambda x: x.get('created_at',''), reverse=True)
    except Exception:
        pass

    return render_template("express_partner/commissions.html",
                           items=my_comms,
                           total_commission=total_commission,
                           pending_commission=pending_commission,
                           paid_commission=paid_commission,
                           sold_count=sold_count,
                           hide_header=True, SHOW_SUBMIT_BUTTON=False,
                           brand="وینور", domain="vinor.ir")


@express_partner_bp.post('/notes/add')
def add_note():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    content = (request.form.get("content") or "").strip()
    if not content:
        return redirect(url_for("express_partner.dashboard"))
    items = load_partner_notes() or []
    new_id = (max([int(x.get('id',0) or 0) for x in items if isinstance(x, dict)], default=0) or 0) + 1
    items.append({"id": new_id, "phone": me_phone, "content": content, "created_at": datetime.utcnow().isoformat()+"Z"})
    save_partner_notes(items)
    try:
        ref = request.referrer or ""
    except Exception:
        ref = ""
    if "/express/partner/notes" in ref:
        return redirect(url_for("express_partner.notes"))
    nxt = (request.form.get("next") or request.args.get("next") or "").strip()
    if nxt.startswith("/express/partner/notes"):
        return redirect(nxt)
    return redirect(url_for("express_partner.dashboard"))


@express_partner_bp.post('/notes/<int:nid>/delete')
def delete_note(nid: int):
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    items = load_partner_notes() or []
    items = [n for n in items if not (int(n.get('id',0) or 0) == int(nid) and str(n.get('phone')) == me_phone)]
    save_partner_notes(items)
    try:
        ref = request.referrer or ""
    except Exception:
        ref = ""
    if "/express/partner/notes" in ref:
        return redirect(url_for("express_partner.notes"))
    nxt = (request.form.get("next") or request.args.get("next") or "").strip()
    if nxt.startswith("/express/partner/notes"):
        return redirect(nxt)
    return redirect(url_for("express_partner.dashboard"))


@express_partner_bp.post('/sales/add')
def add_sale():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    title = (request.form.get("title") or "").strip()
    amount = (request.form.get("amount") or "").strip()
    note = (request.form.get("note") or "").strip()
    if not title:
        return redirect(url_for("express_partner.dashboard"))
    items = load_partner_sales() or []
    new_id = (max([int(x.get('id',0) or 0) for x in items if isinstance(x, dict)], default=0) or 0) + 1
    try:
        amount_num = int(str(amount).replace(',', '').strip() or '0')
    except Exception:
        amount_num = 0
    items.append({
        "id": new_id,
        "phone": me_phone,
        "title": title,
        "amount": amount_num,
        "note": note,
        "created_at": datetime.utcnow().isoformat()+"Z"
    })
    save_partner_sales(items)
    return redirect(url_for("express_partner.dashboard"))


@express_partner_bp.post('/files/upload')
def upload_file():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    f = request.files.get('file')
    if not f or not f.filename:
        return redirect(url_for("express_partner.dashboard"))
    base = os.path.join(current_app.instance_path, 'data', 'uploads', 'partner', me_phone)
    os.makedirs(base, exist_ok=True)
    tsname = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + "__" + f.filename
    safe_name = tsname.replace('..','_').replace('/','_').replace('\\','_')
    path = os.path.join(base, safe_name)
    f.save(path)
    metas = load_partner_files_meta() or []
    new_id = (max([int(x.get('id',0) or 0) for x in metas if isinstance(x, dict)], default=0) or 0) + 1
    metas.append({"id": new_id, "phone": me_phone, "filename": safe_name, "stored_at": datetime.utcnow().isoformat()+"Z"})
    save_partner_files_meta(metas)
    return redirect(url_for("express_partner.dashboard"))


@express_partner_bp.get('/files/<int:fid>/download')
def download_file(fid: int):
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))


# -------------------------
# Auth (Express Partner themed)
# -------------------------
@express_partner_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        phone_raw = request.form.get('phone', '')
        phone = _normalize_phone(phone_raw)
        if not phone or len(phone) != 11:
            flash('شماره موبایل معتبر نیست.', 'error')
            return redirect(url_for('express_partner.login'))

        code = f"{random.randint(10000, 99999)}"
        session.update({'otp_code': code, 'otp_phone': phone})
        session.permanent = True

        # Try sending SMS; ignore errors in dev
        try:
            from ..services.sms import send_sms_code
            send_sms_code(phone, code)
            flash('کد تأیید ارسال شد.', 'info')
        except Exception:
            flash('کد تأیید ارسال شد.', 'info')

        nxt = request.args.get('next')
        if nxt:
            session['next'] = nxt
        return render_template('express_partner/auth/login_step2.html', phone=phone)
    return render_template('express_partner/auth/login_step1.html')


@express_partner_bp.route('/verify', methods=['POST'], endpoint='verify')
def verify():
    code = (request.form.get('otp_code') or '').strip()
    phone = _normalize_phone(request.form.get('phone') or '')
    if not code or not phone:
        flash('اطلاعات ناقص است.', 'error')
        return redirect(url_for('express_partner.login'))

    if session.get('otp_code') == code and session.get('otp_phone') == phone:
        session['user_id'] = phone
        session['user_phone'] = phone
        session.permanent = True
        # ensure user exists
        try:
            from ..utils.storage import load_users, save_users
            users = load_users()
            if not any(u.get('phone') == phone for u in users):
                from datetime import datetime
                users.append({'phone': phone, 'registered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                save_users(users)
        except Exception:
            pass
        flash('✅ ورود موفقیت‌آمیز بود.', 'success')
        return redirect(session.pop('next', None) or url_for('express_partner.dashboard'))

    flash('❌ کد واردشده نادرست است.', 'error')
    return redirect(url_for('express_partner.login'))


@express_partner_bp.route('/support', methods=['GET'], endpoint='support')
def support():
    """صفحه پشتیبانی مجزا برای Express Partner"""
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.support")))
    
    return render_template('express_partner/support.html', hide_header=True)


@express_partner_bp.route('/mark-in-transaction/<code>', methods=['POST'], endpoint='mark_in_transaction')
def mark_in_transaction(code: str):
    """Toggle وضعیت ملک بین در حال معامله و فعال"""
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.dashboard")))
    
    me_phone = (session.get("user_phone") or "").strip()
    
    try:
        assignments = load_express_assignments() or []
        updated = False
        new_status = None
        
        for a in assignments:
            if (str(a.get('land_code')) == str(code) and 
                str(a.get('partner_phone')) == me_phone):
                current_status = a.get('status', 'active')
                # Toggle: اگر در حال معامله است، به active برگردان، وگرنه به in_transaction تغییر بده
                if current_status == 'in_transaction':
                    new_status = 'active'
                    a['status'] = 'active'
                else:
                    new_status = 'in_transaction'
                    a['status'] = 'in_transaction'
                a['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                updated = True
                break
        
        if updated:
            save_express_assignments(assignments)
            if new_status == 'in_transaction':
                flash('✅ ملک به عنوان "در حال معامله" علامت‌گذاری شد.', 'success')
            else:
                flash('✅ وضعیت ملک به "فعال" تغییر یافت.', 'success')
        else:
            flash('❌ ملک یافت نشد یا دسترسی ندارید.', 'error')
    except Exception as e:
        current_app.logger.error(f"Error toggling land transaction status: {e}")
        flash('❌ خطا در بروزرسانی وضعیت.', 'error')
    
    return redirect(url_for('express_partner.dashboard'))


@express_partner_bp.route('/logout', methods=['GET'], endpoint='logout')
def logout():
    # پاک کردن کامل session برای خروج کامل از حساب
    session.clear()
    session.permanent = False
    flash('از حساب خارج شدید.', 'info')
    return redirect(url_for('express_partner.login'))


@express_partner_bp.route('/otp/resend', methods=['POST'], endpoint='otp_resend')
def otp_resend():
    phone = _normalize_phone(request.form.get('phone') or (session.get('otp_phone') or ''))
    if not phone or len(phone) != 11:
        return {'ok': False, 'error': 'شماره معتبر نیست.'}, 400
    try:
        code = f"{random.randint(10000, 99999)}"
        session.update({'otp_code': code, 'otp_phone': phone})
        from ..services.sms import send_sms_code
        send_sms_code(phone, code)
        return {'ok': True}
    except Exception:
        return {'ok': True}


@express_partner_bp.route('/profile', methods=['GET'], endpoint='profile')
def profile_page():
    if not session.get('user_phone'):
        return redirect(url_for('express_partner.login', next=url_for('express_partner.profile')))
    me_phone = (session.get('user_phone') or '').strip()
    return render_template('express_partner/profile.html', me_phone=me_phone)
    me_phone = (session.get("user_phone") or "").strip()
    metas = load_partner_files_meta() or []
    meta = next((m for m in metas if int(m.get('id',0) or 0) == int(fid) and str(m.get('phone')) == me_phone), None)
    if not meta:
        abort(404)
    base = os.path.join(current_app.instance_path, 'data', 'uploads', 'partner', me_phone)
    fp = os.path.join(base, meta.get('filename') or '')
    if not (os.path.isfile(fp)):
        abort(404)
    return send_from_directory(base, os.path.basename(fp), as_attachment=True)


@express_partner_bp.post('/files/<int:fid>/delete')
def delete_file(fid: int):
    if not session.get("user_phone"):
        return redirect(url_for("main.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    metas = load_partner_files_meta() or []
    kept = []
    removed = None
    for m in metas:
        try:
            if int(m.get('id',0) or 0) == int(fid) and str(m.get('phone')) == me_phone:
                removed = m
            else:
                kept.append(m)
        except Exception:
            kept.append(m)
    save_partner_files_meta(kept)
    if removed:
        try:
            base = os.path.join(current_app.instance_path, 'data', 'uploads', 'partner', me_phone)
            fp = os.path.join(base, removed.get('filename') or '')
            if os.path.isfile(fp):
                os.remove(fp)
        except Exception:
            pass
    return redirect(url_for("express_partner.dashboard"))


@express_partner_bp.post('/sales/<int:sid>/update')
def update_sale(sid: int):
    if not session.get("user_phone"):
        return redirect(url_for("main.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    items = load_partner_sales() or []
    for s in items:
        try:
            if int(s.get('id',0) or 0) == int(sid) and str(s.get('phone')) == me_phone:
                title = (request.form.get("title") or "").strip() or s.get('title')
                amount = (request.form.get("amount") or "").strip()
                note = (request.form.get("note") or "").strip()
                try:
                    amount_num = int(str(amount).replace(',', '').strip()) if amount else s.get('amount') or 0
                except Exception:
                    amount_num = s.get('amount') or 0
                s.update({ 'title': title, 'amount': amount_num, 'note': note })
                break
        except Exception:
            continue
    save_partner_sales(items)
    return redirect(url_for("express_partner.dashboard"))


@express_partner_bp.post('/sales/<int:sid>/delete')
def delete_sale(sid: int):
    if not session.get("user_phone"):
        return redirect(url_for("main.login", next=url_for("express_partner.dashboard")))
    me_phone = (session.get("user_phone") or "").strip()
    items = load_partner_sales() or []
    items = [s for s in items if not (int(s.get('id',0) or 0) == int(sid) and str(s.get('phone')) == me_phone)]
    save_partner_sales(items)
    return redirect(url_for("express_partner.dashboard"))


# -------------------------
# Notifications API
# -------------------------
@express_partner_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get user notifications"""
    if not session.get("user_phone"):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    me_phone = (session.get("user_phone") or "").strip()
    notifications = get_user_notifications(me_phone, limit=50)
    return jsonify({
        "success": True,
        "notifications": notifications,
        "unread_count": unread_count(me_phone)
    })


@express_partner_bp.route('/api/notifications/unread-count', methods=['GET'])
def get_unread_count():
    """Get unread notifications count"""
    if not session.get("user_phone"):
        return jsonify({"success": False, "unread_count": 0})
    me_phone = (session.get("user_phone") or "").strip()
    return jsonify({
        "success": True,
        "unread_count": unread_count(me_phone)
    })


@express_partner_bp.route('/api/notifications/<string:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id: str):
    """Mark a notification as read"""
    if not session.get("user_phone"):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    me_phone = (session.get("user_phone") or "").strip()
    success = mark_read(me_phone, notif_id)
    return jsonify({
        "success": success,
        "unread_count": unread_count(me_phone)
    })


@express_partner_bp.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications as read"""
    if not session.get("user_phone"):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    me_phone = (session.get("user_phone") or "").strip()
    count = mark_all_read(me_phone)
    return jsonify({
        "success": True,
        "marked_count": count,
        "unread_count": 0
    })


@express_partner_bp.get('/lands/<string:code>', endpoint='land_detail')
def land_detail(code: str):
    """Express land detail page within partner panel."""
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.land_detail", code=code)))

    lands = load_ads_cached() or []
    land = next((l for l in lands if l.get('code') == code and l.get('is_express')), None)

    if not land:
        flash('آگهی اکسپرس یافت نشد.', 'warning')
        return redirect(url_for('express_partner.dashboard'))

    partners = load_express_partners() or []
    me_phone = (session.get("user_phone") or "").strip()
    partner_profile = next((p for p in partners if str(p.get("phone")) == me_phone), None)

    share_token = encode_partner_ref(me_phone)
    share_url = url_for("main.express_detail", code=code, ref=share_token, _external=True)

    return render_template(
        'express_partner/land_detail.html',
        land=land,
        share_url=share_url,
        share_token=share_token,
        partner_profile=partner_profile,
        brand="وینور",
        domain="vinor.ir"
    )


