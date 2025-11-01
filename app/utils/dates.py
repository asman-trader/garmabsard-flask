# app/utils/dates.py
from datetime import datetime, timedelta
from typing import Optional

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

def utcnow() -> datetime:
    """برگرداندن زمان UTC فعلی"""
    return datetime.utcnow()

def iso_z(dt: datetime) -> str:
    """تبدیل datetime به فرمت ISO 8601 با Z (UTC)"""
    return dt.replace(microsecond=0).isoformat() + "Z"

def parse_iso_to_naive_utc(s: str) -> Optional[datetime]:
    """تبدیل رشته ISO 8601 به datetime (naive UTC)"""
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        return dt.replace(tzinfo=None)
    except Exception:
        return None

def is_ad_expired(ad: dict) -> bool:
    """بررسی انقضای آگهی"""
    exp_str = ad.get("expires_at")
    if not exp_str:
        return False  # آگهی نامحدود، منقضی نشده
    exp_dt = parse_iso_to_naive_utc(exp_str)
    if exp_dt is None:
        return False  # تاریخ نامعتبر، منقضی محسوب نمی‌شود
    return exp_dt < utcnow()
