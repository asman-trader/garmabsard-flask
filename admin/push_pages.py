from __future__ import annotations

from flask import render_template, request, jsonify

from .blueprint import admin_bp
from .routes import login_required  # reuse decorator
from app.api.push import _load_subs, _save_subs, _send_one


@admin_bp.get('/push-test')
@login_required
def admin_push_test():
    return render_template('admin/push_test.html')


@admin_bp.post('/push-test')
@login_required
def admin_push_test_send():
    title = (request.form.get('title') or '').strip() or 'وینور – اعلان آزمایشی'
    body  = (request.form.get('body')  or '').strip() or 'این یک پیام آزمایشی از پنل ادمین است.'
    url   = (request.form.get('url')   or '').strip() or '/notifications'

    payload = {
        'title': title,
        'body': body,
        'url': url,
        'icon': '/static/icons/icon-192.png',
        'tag':  'vinor-push-test'
    }

    subs = _load_subs()
    if not subs:
        return jsonify({'ok': False, 'error': 'NO_SUBSCRIBERS'}), 400

    sent = removed = failed = 0
    alive = []
    for s in subs:
        r = _send_one(s, payload)
        if r.get('ok'):
            sent += 1
            alive.append(s)
        else:
            if r.get('remove'):
                removed += 1
            else:
                failed += 1

    _save_subs(alive)

    return jsonify({
        'ok': True,
        'sent': sent,
        'removed': removed,
        'failed': failed,
        'remaining': len(alive)
    })


