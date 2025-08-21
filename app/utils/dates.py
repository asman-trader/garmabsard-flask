# app/utils/dates.py
from datetime import datetime

def parse_datetime_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                pass
    return datetime(1970, 1, 1)
