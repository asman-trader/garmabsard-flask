# app/routes/auth.py
from datetime import datetime
import random
from flask import render_template, request, session, redirect, url_for, flash
from . import main_bp
from ..services.sms import send_sms_code
from ..utils.storage import load_users, save_users

@main_bp.route('/login', methods=['GET','POST'])
def send_otp():
    if request.method == 'POST':
        phone = request.form.get('phone')
        if not phone:
            flash("شماره موبایل الزامی است.")
            return redirect(url_for('main.send_otp'))
        code = str(random.randint(10000, 99999))
        session.update({'otp_code': code, 'otp_phone': phone})
        send_sms_code(phone, code)
        return render_template('login_step2.html', phone=phone)
    return render_template('login_step1.html')

@main_bp.route('/verify', methods=['POST'])
def verify_otp():
    code  = request.form.get('otp_code')
    phone = request.form.get('phone')
    if not code or not phone:
        flash("اطلاعات ناقص است.")
        return redirect(url_for('main.send_otp'))

    if session.get('otp_code') == code and session.get('otp_phone') == phone:
        session['user_phone'] = phone
        users = load_users()
        if not any(u.get('phone') == phone for u in users):
            users.append({'phone': phone, 'registered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            save_users(users)
        flash("✅ ورود موفقیت‌آمیز بود.")
        return redirect(session.pop('next', None) or url_for('main.index'))
    flash("❌ کد واردشده نادرست است.")
    return redirect(url_for('main.send_otp'))

@main_bp.route('/logout')
def logout():
    session.pop('user_phone', None)
    flash("از حساب خارج شدید.")
    return redirect(url_for('main.index'))
