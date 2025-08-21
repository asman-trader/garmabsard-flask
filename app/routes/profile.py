# app/routes/profile.py
from flask import render_template, request, session, redirect, url_for, flash
from . import main_bp
from ..utils.storage import load_users, save_users

@main_bp.route('/profile')
def profile():
    if 'user_phone' not in session:
        flash("برای مشاهده پروفایل وارد شوید.")
        session['next'] = url_for('main.profile')
        return redirect(url_for('main.send_otp'))
    users = load_users()
    user = next((u for u in users if u.get('phone') == session['user_phone']), None)
    return render_template('profile.html', user=user)

@main_bp.route('/settings', methods=['GET','POST'])
def settings():
    if 'user_phone' not in session:
        flash("برای ورود به تنظیمات وارد شوید.")
        session['next'] = url_for('main.settings')
        return redirect(url_for('main.send_otp'))

    users = load_users()
    phone = session['user_phone']
    user = next((u for u in users if u.get('phone') == phone), None)
    if not user:
        flash("کاربر یافت نشد.")
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        user['name']      = request.form.get('name','').strip()
        user['lastname']  = request.form.get('lastname','').strip()
        user['province']  = request.form.get('province','').strip()
        user['city']      = request.form.get('city','').strip()
        new_password      = request.form.get('password','').strip()
        if new_password: user['password'] = new_password
        save_users(users)
        flash("✅ تنظیمات ذخیره شد.")
        return redirect(url_for('main.settings'))
    return render_template('settings.html', user=user)

@main_bp.route('/favorites')
def favorites():
    return render_template('favorites.html')
