from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash

from .blueprint import admin_bp
from .routes import counts_by_status, load_json, _lands_path  # reuse helpers
from app.services.sms import send_sms_template
import time


@admin_bp.route('/sms-campaign', methods=['GET', 'POST'])
def sms_campaign():
    if request.method == 'GET':
        p, a, r = counts_by_status(load_json(_lands_path()) or [])
        return render_template('admin/sms_campaign.html', pending_count=p, approved_count=a, rejected_count=r)

    _ = request.form.get('csrf_token')

    file = request.files.get('numbers_file')
    numbers_text = (request.form.get('numbers_text') or '').strip()
    template_id_raw = (request.form.get('template_id') or '').strip()
    delay_ms_raw = (request.form.get('delay_ms') or '1000').strip()

    params: dict[str, str] = {}
    for k, v in request.form.items():
        if k.startswith('p[') and k.endswith(']'):
            key = k[2:-1].strip()
            if key:
                params[key] = v
        elif k.startswith('p.'):
            key = k[2:].strip()
            if key:
                params[key] = v

    if not file or not file.filename.lower().endswith('.txt'):
        flash('لطفاً یک فایل txt از شماره‌ها ارسال کنید.', 'warning')
        return redirect(url_for('admin.sms_campaign'))

    try:
        template_id = int(template_id_raw)
    except Exception:
        flash('شناسهٔ قالب (template_id) نامعتبر است.', 'danger')
        return redirect(url_for('admin.sms_campaign'))

    try:
        delay_ms = max(0, int(delay_ms_raw))
    except Exception:
        delay_ms = 1000

    file_numbers: list[str] = []
    if file and file.filename:
        try:
            content = file.read().decode('utf-8', errors='ignore')
        except Exception:
            content = file.read().decode('cp1256', errors='ignore') if file else ''
        file_numbers = [line.strip() for line in content.splitlines() if line.strip()]

    text_numbers: list[str] = []
    if numbers_text:
        text_numbers = [line.strip() for line in numbers_text.splitlines() if line.strip()]

    numbers = file_numbers + text_numbers
    # حذف تکراری‌ها (اختیاری)
    if request.form.get('dedupe') == 'on':
        seen = set()
        uniq = []
        for n in numbers:
            if n not in seen:
                uniq.append(n)
                seen.add(n)
        numbers = uniq

    # اعتبارسنجی الگوی موبایل ایران (اختیاری ساده)
    if request.form.get('validate_ir') == 'on':
        filtered = []
        for n in numbers:
            s = n.replace(' ', '')
            if s.startswith('+98') and len(s) == 13:
                filtered.append(s)
            elif s.startswith('0098') and len(s) == 14:
                filtered.append('+98' + s[4:])
            elif s.startswith('0') and len(s) == 11:
                filtered.append('+98' + s[1:])
            elif s.startswith('9') and len(s) == 10:
                filtered.append('+98' + s)
            else:
                # عبور دادن شماره‌هایی که شاید فرمت دیگری داشته باشند
                filtered.append(s)
        numbers = filtered
    if not numbers:
        flash('هیچ شماره‌ای در فایل یافت نشد.', 'warning')
        return redirect(url_for('admin.sms_campaign'))

    sent = failed = 0
    results = []
    # حالت تاخیر تصادفی
    mode = request.form.get('delay_mode') or 'fixed'
    min_ms = max(0, int((request.form.get('delay_min_ms') or '800') or 800)) if mode == 'random' else None
    max_ms = max(0, int((request.form.get('delay_max_ms') or '1800') or 1800)) if mode == 'random' else None
    if min_ms is not None and max_ms is not None and min_ms > max_ms:
        min_ms, max_ms = max_ms, min_ms

    dry_run = request.form.get('dry_run') == 'on'

    import random

    for mobile in numbers:
        if dry_run:
            resp = {"ok": True, "status": 200}
        else:
            resp = send_sms_template(mobile=mobile, template_id=template_id, parameters=params)
        if resp.get('ok'):
            sent += 1
        else:
            failed += 1
        results.append({
            'mobile': mobile,
            'ok': bool(resp.get('ok')),
            'status': resp.get('status'),
        })
        if mode == 'fixed':
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
        else:
            lo = min_ms or 0
            hi = max_ms or lo
            wait_ms = random.randint(lo, hi) if hi >= lo else lo
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)

    flash(f'ارسال کامل شد: موفق {sent} | ناموفق {failed}', 'success' if failed == 0 else 'warning')
    p, a, r = counts_by_status(load_json(_lands_path()) or [])
    return render_template(
        'admin/sms_campaign.html',
        summary={'sent': sent, 'failed': failed, 'total': len(numbers)},
        results=results[:200],
        pending_count=p, approved_count=a, rejected_count=r,
    )
