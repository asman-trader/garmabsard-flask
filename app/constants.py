# app/constants.py
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
