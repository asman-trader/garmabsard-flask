# -*- coding: utf-8 -*-
from flask import Blueprint

# اسم بلواپرینت «main» است تا endpointها به شکل main.xxx ثبت شوند
main_bp = Blueprint(
    "main",
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# ⬇️ بسیار مهم: این ایمپورت‌ها باید بعد از تعریف main_bp باشند
# با این کار، تمام روت‌های ماژول‌ها رجیستر می‌شوند
from . import public       # صفحات عمومی (لندینگ همکاران و جزئیات اکسپرس)

__all__ = ["main_bp"]
