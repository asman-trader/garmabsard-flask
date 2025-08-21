# app/filters.py
from datetime import datetime

def _parse_any_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                pass
    return None

def date_ymd(value, default="-"):
    dt = _parse_any_date(value)
    if dt:
        return dt.strftime("%Y/%m/%d")
    if isinstance(value, str) and value:
        return value.split(" ")[0].replace("-", "/")
    return default

def basename(value):
    if value is None:
        return ""
    s = str(value).replace("\\", "/")
    return s.rsplit("/", 1)[-1]

def register_filters(app):
    app.add_template_filter(date_ymd, "date_ymd")
    app.add_template_filter(basename, "basename")
