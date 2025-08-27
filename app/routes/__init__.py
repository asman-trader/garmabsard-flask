# app/routes/__init__.py
from flask import Blueprint

# اسم بلواپرینت «main» است تا endpointها به شکل main.xxx ثبت شوند
main_bp = Blueprint("main", __name__, template_folder="../templates", static_folder="../static")

# ⬇️ بسیار مهم: این ایمپورت‌ها باید بعد از تعریف main_bp باشند
# با این کار، تمام روت‌های ماژول‌ها رجیستر می‌شوند (از جمله profile و auth)
from . import public     # صفحه /app و صفحات عمومی
from . import ads        # آگهی‌ها
from . import auth       # ورود/تأیید/خروج  -> endpoints: main.login, main.verify, main.logout
from . import profile    # پروفایل/تنظیمات/علاقه‌مندی‌ها -> endpoints: main.profile, main.settings, main.favorites
from . import admin      # پنل ادمین
from . import notifications
from . import diagnostics
from . import webhook

__all__ = ["main_bp"]
