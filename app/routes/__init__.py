# app/routes/__init__.py
from flask import Blueprint

# بلوپرینت عمومی وینور
main_bp = Blueprint("main", __name__)

# فقط ماژول‌های روت را بارگذاری کن تا روی main_bp روت‌ها رجیستر شوند.
# ⚠️ هیچ ایمپورتی از filters در این فایل نداشته باش!
from . import public  # noqa: E402,F401

__all__ = ["main_bp"]

