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

    try:
        content = file.read().decode('utf-8', errors='ignore')
    except Exception:
        content = file.read().decode('cp1256', errors='ignore') if file else ''
    numbers = [line.strip() for line in content.splitlines() if line.strip()]
    if not numbers:
        flash('هیچ شماره‌ای در فایل یافت نشد.', 'warning')
        return redirect(url_for('admin.sms_campaign'))

    sent = failed = 0
    results = []
    for mobile in numbers:
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
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

    flash(f'ارسال کامل شد: موفق {sent} | ناموفق {failed}', 'success' if failed == 0 else 'warning')
    p, a, r = counts_by_status(load_json(_lands_path()) or [])
    return render_template(
        'admin/sms_campaign.html',
        summary={'sent': sent, 'failed': failed, 'total': len(numbers)},
        results=results[:200],
        pending_count=p, approved_count=a, rejected_count=r,
    )
