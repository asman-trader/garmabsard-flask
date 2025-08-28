# app/routes/notifications.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Any
from flask import render_template, session, redirect, url_for, flash
from . import main_bp
from ..utils.storage import load_notifications, save_notifications


# ---------- Helpers ----------
def _user_phone() -> str | None:
    return session.get("user_phone")

def _user_items(phone: str | None) -> List[Dict[str, Any]]:
    if not phone:
        return []
    return [n for n in load_notifications() if n.get("to") == phone]

def user_unread_notifications_count(phone: str | None) -> int:
    if not phone:
        return 0
    return sum(1 for n in _user_items(phone) if not n.get("read"))


# این مقدار به همهٔ تمپلیت‌ها تزریق می‌شود (برای نشان‌دادن Badge)
@main_bp.app_context_processor
def inject_notifications_count():
    phone = _user_phone()
    return {"notif_count": user_unread_notifications_count(phone)}


# ---------- Routes ----------
@main_bp.route("/notifications")
def notifications():
    phone = _user_phone()
    if not phone:
        flash("برای دیدن اعلان‌ها ابتدا وارد شوید.", "warning")
        return redirect(url_for("main.send_otp"))

    items = _user_items(phone)
    # مرتب‌سازی: اول بر اساس created_at (در صورت وجود)، بعد id
    items.sort(
        key=lambda n: (
            0 if n.get("created_at") is None else 1,
            n.get("created_at") or n.get("id") or 0
        ),
        reverse=True,
    )

    # enable_push_ui -> صفحه می‌تواند دکمه‌های «اجازه اعلان» و «آزمایش» را نشان دهد
    return render_template(
        "notifications.html",
        items=items,
        enable_push_ui=True,
        page_title="اعلان‌ها | وینور (Vinor)"
    )


@main_bp.route("/notifications/read-all", methods=["POST"])
def notifications_read_all():
    phone = _user_phone()
    if not phone:
        flash("ابتدا وارد شوید.", "warning")
        return redirect(url_for("main.send_otp"))

    items = load_notifications()
    changed = False
    for n in items:
        if n.get("to") == phone and not n.get("read"):
            n["read"] = True
            changed = True

    if changed:
        save_notifications(items)
        flash("همه اعلان‌ها خوانده شد.", "success")
    else:
        flash("اعلان خوانده‌نشده‌ای یافت نشد.", "info")

    return redirect(url_for("main.notifications"))
