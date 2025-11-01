# app/constants.py
# دسته‌بندی قدیم (برای سازگاری با آگهی‌های موجود)
CATEGORY_MAP = {
    "": "همه آگهی‌ها",
    "residential_land": "زمین مسکونی",
    "garden": "باغ",
    "villa": "ویلا",
    "titled": "سنددار",
    "with_utilities": "دارای آب و برق",
    "good_price": "قیمت مناسب",
}
CATEGORY_KEYS = set(CATEGORY_MAP.keys()) - {""}

# برای استفاده از ساختار جدید، از app.categories استفاده کنید
try:
    from .categories import CATEGORIES
except ImportError:
    CATEGORIES = {}
