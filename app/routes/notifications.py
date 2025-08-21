# app/routes/notifications.py
from flask import render_template, session, redirect, url_for, flash
from . import main_bp
from ..utils.storage import load_notifications, save_notifications

def user_unread_notifications_count(phone):
    if not phone: return 0
    items = load_notifications()
    return sum(1 for n in items if n.get('to') == phone and not n.get('read'))

@main_bp.app_context_processor
def inject_notifications_count():
    phone = session.get('user_phone')
    return {'notif_count': user_unread_notifications_count(phone)}

@main_bp.route('/notifications')
def notifications():
    phone = session.get('user_phone')
    if not phone:
        flash('برای دیدن اعلان‌ها ابتدا وارد شوید.', 'warning')
        return redirect(url_for('main.send_otp'))
    items = [n for n in load_notifications() if n.get('to') == phone]
    items.sort(key=lambda n: n.get('created_at') or n.get('id') or 0, reverse=True)
    return render_template('notifications.html', items=items)

@main_bp.route('/notifications/read-all', methods=['POST'])
def notifications_read_all():
    phone = session.get('user_phone')
    if not phone:
        flash('ابتدا وارد شوید.', 'warning')
        return redirect(url_for('main.send_otp'))
    items = load_notifications()
    changed = False
    for n in items:
        if n.get('to') == phone and not n.get('read'):
            n['read'] = True; changed = True
    if changed: save_notifications(items)
    flash('همه اعلان‌ها خوانده شد.', 'success')
    return redirect(url_for('main.notifications'))
