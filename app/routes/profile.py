# app/routes/profile.py
from flask import render_template, request, session, redirect, url_for, flash
from . import main_bp
from ..utils.storage import load_users, save_users
from ..utils.storage import (
    load_consultant_apps, load_consultants,
    load_express_partners, load_express_partner_apps,
    load_partner_notes, load_partner_sales, load_partner_files_meta,
)

# -------------------------
# Helpers
# -------------------------
def _require_login(next_endpoint: str):
    """اگر لاگین نیست، next را ست کند و به صفحه ورود ببرد."""
    if not session.get("user_phone"):
        flash("برای دسترسی به این بخش ابتدا وارد شوید.", "error")
        session["next"] = url_for(next_endpoint)
        return redirect(url_for("main.login"))
    return None

# -------------------------
# Routes (با نام‌های ثابت برای تمپلیت)
# -------------------------

@main_bp.route("/profile", methods=["GET"], endpoint="profile")
def profile():
    # نیاز به ورود
    guard = _require_login("main.profile")
    if guard:
        return guard

    users = load_users()
    phone = session.get("user_phone")
    user = next((u for u in users if u.get("phone") == phone), None)

    # Consultant info
    consultants = load_consultants() or []
    consultant_profile = next((c for c in consultants if str(c.get("phone")) == str(phone)), None)
    consultant_apps = [a for a in (load_consultant_apps() or []) if str(a.get("phone")) == str(phone)]

    # Express partner info
    partners = load_express_partners() or []
    partner_profile = next((p for p in partners if str(p.get("phone")) == str(phone)), None)
    partner_notes = [n for n in (load_partner_notes() or []) if str(n.get("phone")) == str(phone)]
    partner_sales = [s for s in (load_partner_sales() or []) if str(s.get("phone")) == str(phone)]
    partner_files = [f for f in (load_partner_files_meta() or []) if str(f.get("phone")) == str(phone)]

    # Totals (monthly/yearly)
    from datetime import datetime
    def _ym(dtstr):
        try:
            return datetime.fromisoformat((dtstr or '').replace('Z','+00:00')).strftime('%Y-%m')
        except Exception:
            return ''
    def _year(dtstr):
        try:
            return datetime.fromisoformat((dtstr or '').replace('Z','+00:00')).strftime('%Y')
        except Exception:
            return ''
    monthly = {}
    yearly = {}
    for s in partner_sales:
        y = _year(s.get('created_at') or '')
        ym = _ym(s.get('created_at') or '')
        amt = int(s.get('amount') or 0)
        if y:
            yearly[y] = yearly.get(y, 0) + amt
        if ym:
            monthly[ym] = monthly.get(ym, 0) + amt

    return render_template(
        "account/profile.html",
        user=user,
        consultant_profile=consultant_profile,
        consultant_apps=consultant_apps,
        partner_profile=partner_profile,
        partner_notes=partner_notes,
        partner_sales=partner_sales,
        partner_files=partner_files,
        partner_sales_monthly=monthly,
        partner_sales_yearly=yearly,
    )


@main_bp.route("/settings", methods=["GET", "POST"], endpoint="settings")
def settings():
    # نیاز به ورود
    guard = _require_login("main.settings")
    if guard:
        return guard

    users = load_users()
    phone = session.get("user_phone")
    user = next((u for u in users if u.get("phone") == phone), None)

    if not user:
        flash("کاربر یافت نشد.", "error")
        return redirect(url_for("main.profile"))

    if request.method == "POST":
        user["name"]     = (request.form.get("name") or "").strip()
        user["lastname"] = (request.form.get("lastname") or "").strip()
        user["province"] = (request.form.get("province") or "").strip()
        user["city"]     = (request.form.get("city") or "").strip()
        new_password     = (request.form.get("password") or "").strip()
        if new_password:
            user["password"] = new_password

        save_users(users)
        flash("✅ تنظیمات با موفقیت ذخیره شد.", "success")
        return redirect(url_for("main.settings"))

    return render_template("account/settings.html", user=user)


@main_bp.route("/favorites", methods=["GET"], endpoint="favorites")
def favorites():
    # (در صورت نیاز، موارد نیازمند ورود را هم محافظت کن)
    return render_template("account/favorites.html")
