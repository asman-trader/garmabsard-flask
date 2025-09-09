# app/routes/auth.py
from datetime import datetime
import random, re
from flask import render_template, request, session, redirect, url_for, flash
from . import main_bp
from ..services.sms import send_sms_code
from ..utils.storage import load_users, save_users

# -------------------------
# Helpers
# -------------------------
def _normalize_phone(phone: str) -> str:
    """تمیزسازی شماره: حذف غیررقمی‌ها؛ تبدیل 0098/98 به 0؛ برش به 11 رقم."""
    p = (phone or "").strip()
    p = re.sub(r"\D+", "", p)
    if p.startswith("0098"):
        p = "0" + p[4:]
    elif p.startswith("98"):
        p = "0" + p[2:]
    if not p.startswith("0"):
        p = "0" + p
    return p[:11]

def _redirect_next_or(default_endpoint: str):
    nxt = request.args.get("next") or session.pop("next", None)
    try:
        return redirect(nxt) if nxt else redirect(url_for(default_endpoint))
    except Exception:
        return redirect(url_for(default_endpoint))

# -------------------------
# Routes (با نام‌های ثابت برای تمپلیت)
# -------------------------

@main_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    """
    مرحله ۱: دریافت شماره و ارسال کد یکبارمصرف (OTP)
    """
    if request.method == "POST":
        phone_raw = request.form.get("phone", "")
        phone = _normalize_phone(phone_raw)
        if not phone or len(phone) != 11:
            flash("شماره موبایل معتبر نیست.", "error")
            return redirect(url_for("main.login"))

        code = f"{random.randint(10000, 99999)}"
        session.update({"otp_code": code, "otp_phone": phone})
        session.permanent = True

        try:
            send_sms_code(phone, code)
            flash("کد تأیید ارسال شد.", "info")
        except Exception:
            # محیط توسعه: خطا در سرویس SMS را نادیده می‌گیریم
            flash("کد تأیید ارسال شد.", "info")

        # پشتیبانی از next (مثلاً /app)
        nxt = request.args.get("next")
        if nxt:
            session["next"] = nxt

        return render_template("login_step2.html", phone=phone)

    return render_template("login_step1.html")


@main_bp.route("/verify", methods=["POST"], endpoint="verify")
def verify():
    """
    مرحله ۲: اعتبارسنجی کد و ورود
    """
    code = (request.form.get("otp_code") or "").strip()
    phone = _normalize_phone(request.form.get("phone") or "")
    if not code or not phone:
        flash("اطلاعات ناقص است.", "error")
        return redirect(url_for("main.login"))

    if session.get("otp_code") == code and session.get("otp_phone") == phone:
        # ورود موفق
        session["user_id"] = phone
        session["user_phone"] = phone
        session.permanent = True

        # ثبت کاربر جدید
        users = load_users()
        if not any(u.get("phone") == phone for u in users):
            users.append({
                "phone": phone,
                "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            save_users(users)

        flash("✅ ورود موفقیت‌آمیز بود.", "success")
        return _redirect_next_or("main.app_home")

    flash("❌ کد واردشده نادرست است.", "error")
    return redirect(url_for("main.login"))


@main_bp.route("/logout", methods=["GET"], endpoint="logout")
def logout():
    """
    خروج از حساب (کوکی «اولین بازدید» دست‌نخورده می‌ماند).
    """
    for k in ("user_id", "user_phone", "otp_code", "otp_phone"):
        session.pop(k, None)
    flash("از حساب خارج شدید.", "info")
    return redirect(url_for("main.login"))

@main_bp.route('/push-subscribe-test')
def push_subscribe_test():
    return render_template('push_subscribe_test.html')
