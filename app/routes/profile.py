# app/routes/profile.py
from flask import render_template, request, session, redirect, url_for, flash
from . import main_bp
from ..utils.storage import load_users, save_users

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
    return render_template("account/profile.html", user=user)


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
