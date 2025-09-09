# -*- coding: utf-8 -*-
"""
Vinor User Notifications Routes on main_bp – Final
- Mobile-first، سریع، امن و شفاف
- ساخت امن URL برای استفاده در قالب (بدون نیاز به globals در Jinja)
"""
from flask import jsonify, request, render_template, session, redirect, url_for
from werkzeug.routing import BuildError
from . import main_bp
from app.services.notifications import (
    get_user_notifications,
    unread_count,
    mark_read,
    mark_all_read,
)

# -------------------------------
# کمک‌تابع: شناسه کاربر جاری
# -------------------------------
def current_user_id():
    # در پروژه‌ی شما کلید سشن برای تلفن کاربر "user_phone" است
    return session.get("user_phone")

def ensure_logged_in(redirect_if_needed: bool = False):
    """
    اگر لاگین نیست:
      - در حالت redirect_if_needed=True: ریدایرکت به لاگین + تنظیم next
      - در حالت False: فقط False برمی‌گرداند (برای APIها)
    """
    if not current_user_id():
        if redirect_if_needed:
            session['next'] = url_for("main.notifications")
            return redirect(url_for("main.login"))
        return False
    return True

# -------------------------------
# کمک‌تابع: ساخت امن URL endpoint
# -------------------------------
def _safe_url(endpoint: str, **values) -> str:
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return ""

# ============= صفحات =============
@main_bp.route("/notifications", methods=["GET"], endpoint="notifications")
def notifications_page():
    guard = ensure_logged_in(redirect_if_needed=True)
    if guard is not True:
        return guard  # ریدایرکت به لاگین

    uid = current_user_id()
    items = get_user_notifications(uid, limit=100)

    # URLها در ویو ساخته می‌شوند تا در قالب به‌صورت امن استفاده شوند (مثلاً با |tojson)
    mark_all_read_url = _safe_url("main.api_notifications_mark_all_read")
    mark_one_read_url = _safe_url("main.api_notifications_mark_read")
    unread_count_url  = _safe_url("main.api_notifications_unread_count")

    return render_template(
        "notifications.html",
        items=items,
        mark_all_read_url=mark_all_read_url,
        mark_one_read_url=mark_one_read_url,
        unread_count_url=unread_count_url,
    )

# ============= API =============
@main_bp.route("/api/notifications/unread-count", methods=["GET"], endpoint="api_notifications_unread_count")
def api_unread_count():
    uid = current_user_id()
    if not uid:
        return jsonify({"count": 0})
    return jsonify({"count": unread_count(uid)})

@main_bp.route("/api/notifications/mark-read", methods=["POST"], endpoint="api_notifications_mark_read")
def api_mark_read():
    if not ensure_logged_in():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    uid = current_user_id()
    payload = request.get_json(silent=True) or {}
    notif_id = payload.get("id")
    ok = bool(notif_id) and mark_read(uid, notif_id)
    return jsonify({"ok": bool(ok)})

@main_bp.route("/api/notifications/mark-all-read", methods=["POST"], endpoint="api_notifications_mark_all_read")
def api_mark_all_read():
    if not ensure_logged_in():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    uid = current_user_id()
    updated = mark_all_read(uid)
    return jsonify({"ok": True, "updated": int(updated)})
