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
    load_express_assignments, load_express_commissions,
    load_ads_cached,
)


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


@express_partner_bp.route('/apply', methods=['GET', 'POST'], endpoint='apply')
def apply():
    if not session.get("user_phone"):
        return redirect(url_for("express_partner.login", next=url_for("express_partner.apply")))

    me_phone = (session.get("user_phone") or "").strip()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        city = (request.form.get("city") or "").strip()
        experience = (request.form.get("experience") or "").strip()
        note = (request.form.get("note") or "").strip()

        apps = load_express_partner_apps() or []
        partners = load_express_partners() or []
        if any(str(p.get("phone")) == me_phone for p in partners if isinstance(p, dict)):
            return redirect(url_for("express_partner.dashboard"))

        new_id = (max([int(x.get("id", 0) or 0) for x in apps if isinstance(x, dict)], default=0) or 0) + 1
        apps.append({
            "id": new_id,
            "name": name,
            "phone": me_phone,
            "city": city,
            "experience": experience,
            "note": note,
            "status": "new",
            "created_at": datetime.utcnow().isoformat()+"Z",
        })
        save_express_partner_apps(apps)
        return render_template("express_partner/thanks.html", name=name, brand="وینور", domain="vinor.ir")

    return render_template("express_partner/apply.html", brand="وینور", domain="vinor.ir")


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
    my_assignments = [a for a in assignments if str(a.get('partner_phone')) == me_phone and a.get('status') in (None,'active','pending','approved')]
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


@express_partner_bp.route('/logout', methods=['GET'], endpoint='logout')
def logout():
    for k in ('user_id', 'user_phone', 'otp_code', 'otp_phone'):
        session.pop(k, None)
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


