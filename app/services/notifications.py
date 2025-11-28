# -*- coding: utf-8 -*-
"""
Vinor Notifications Service – سیستم مرکزی مدیریت اعلان‌ها
"""
import time
import uuid
import os
import json
from typing import List, Dict, Any, Optional
from flask import current_app


def _get_notifications_file_path() -> str:
    """مسیر فایل اعلان‌ها"""
    try:
        app = current_app._get_current_object()
        instance_path = app.instance_path
    except Exception:
        instance_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance')
    
    data_dir = os.path.join(instance_path, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'notifications.json')


def _normalize_user_id(user_id: str) -> str:
    """
    Normalize کردن user_id (شماره تلفن) به فرمت استاندارد 09xxxxxxxxx
    این تابع باید در همه جا استفاده شود تا تطابق کامل باشد.
    """
    if not user_id:
        return ""
    
    # تبدیل به string و حذف فاصله‌ها
    user_id = str(user_id).strip()
    
    # حذف همه کاراکترهای غیرعددی
    import re
    normalized = re.sub(r'\D+', '', user_id)
    
    # تبدیل به فرمت استاندارد 09xxxxxxxxx
    if normalized.startswith('0098') and len(normalized) >= 14:
        normalized = '0' + normalized[4:]
    elif normalized.startswith('98') and len(normalized) >= 12:
        normalized = '0' + normalized[2:]
    elif not normalized.startswith('0') and len(normalized) == 10:
        normalized = '0' + normalized
    
    # اطمینان از طول 11 رقم
    if len(normalized) >= 11:
        return normalized[:11]
    elif len(normalized) == 10:
        return '0' + normalized
    else:
        return normalized


def _load_all() -> Dict[str, List[Dict[str, Any]]]:
    """بارگذاری همه اعلان‌ها از فایل"""
    file_path = _get_notifications_file_path()
    
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except Exception as e:
        try:
            current_app.logger.error(f"Error loading notifications: {e}")
        except Exception:
            pass
        return {}
    
    # تبدیل به ساختار استاندارد
    if isinstance(raw, dict):
        # Normalize کردن کلیدها
        normalized_data = {}
        for key, value in raw.items():
            normalized_key = _normalize_user_id(key)
            if normalized_key and isinstance(value, list):
                normalized_data[normalized_key] = [n for n in value if isinstance(n, dict)]
        return normalized_data
    
    # حالت قدیمی: لیست تخت
    if isinstance(raw, list):
        grouped = {}
        for n in raw:
            if not isinstance(n, dict):
                continue
            uid = n.get("user_id") or n.get("uid") or ""
            if uid:
                normalized_uid = _normalize_user_id(uid)
                if normalized_uid:
                    grouped.setdefault(normalized_uid, []).append(n)
        return grouped
    
    return {}


def _save_all(data: Dict[str, List[Dict[str, Any]]]) -> bool:
    """ذخیره همه اعلان‌ها در فایل"""
    file_path = _get_notifications_file_path()
    
    try:
        # Normalize کردن همه کلیدها قبل از ذخیره
        normalized_data = {}
        for key, value in data.items():
            normalized_key = _normalize_user_id(key)
            if normalized_key and isinstance(value, list):
                normalized_data[normalized_key] = value
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(normalized_data, f, ensure_ascii=False, indent=2)
        
        try:
            current_app.logger.info(f"Notifications saved successfully. Total users: {len(normalized_data)}")
        except Exception:
            pass
        
        return True
    except Exception as e:
        try:
            current_app.logger.error(f"Error saving notifications: {e}", exc_info=True)
        except Exception:
            pass
        return False


def add_notification(user_id: str, title: str, body: str, ntype: str = "info",
                     ad_id: Optional[str] = None, action_url: Optional[str] = None) -> Dict[str, Any]:
    """
    افزودن اعلان جدید برای یک کاربر
    """
    if not user_id:
        raise ValueError("user_id is required")
    
    # Normalize کردن user_id
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id or len(normalized_user_id) != 11:
        raise ValueError(f"Invalid user_id format: {user_id} -> {normalized_user_id}")
    
    # بارگذاری داده‌های موجود
    data = _load_all()
    
    # ایجاد اعلان جدید
    notif = {
        "id": str(uuid.uuid4()),
        "title": str(title).strip(),
        "body": str(body).strip(),
        "type": str(ntype).strip() or "info",
        "created_at": int(time.time()),
        "is_read": False,
        "ad_id": ad_id,
        "action_url": action_url,
        "user_id": normalized_user_id,  # ذخیره user_id normalize شده
    }
    
    # افزودن به لیست اعلان‌های کاربر
    if normalized_user_id not in data:
        data[normalized_user_id] = []
    
    data[normalized_user_id].insert(0, notif)
    
    # محدود کردن تعداد اعلان‌ها (حفظ آخرین 100 اعلان)
    if len(data[normalized_user_id]) > 100:
        data[normalized_user_id] = data[normalized_user_id][:100]
    
    # ذخیره
    if not _save_all(data):
        raise RuntimeError("Failed to save notification")
    
    # Logging
    try:
        current_app.logger.info(
            f"Notification added: user_id={normalized_user_id}, title={title}, "
            f"total_notifications={len(data[normalized_user_id])}"
        )
    except Exception:
        pass
    
    return notif


def get_user_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    دریافت اعلان‌های یک کاربر
    """
    if not user_id:
        return []
    
    # Normalize کردن user_id
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        try:
            current_app.logger.warning(f"Invalid user_id after normalization: {user_id}")
        except Exception:
            pass
        return []
    
    # بارگذاری داده‌ها
    data = _load_all()
    
    # Logging برای debug
    try:
        current_app.logger.info(
            f"get_user_notifications: user_id={user_id} -> normalized={normalized_user_id}"
        )
        current_app.logger.info(f"Available keys in storage: {list(data.keys())}")
    except Exception:
        pass
    
    # دریافت اعلان‌های کاربر - اول با کلید normalize شده
    items = data.get(normalized_user_id, [])
    if not isinstance(items, list):
        items = []
    
    # اگر اعلانی پیدا نشد، بررسی همه کلیدها برای تطابق احتمالی
    if not items:
        try:
            current_app.logger.info(f"No direct match for '{normalized_user_id}', searching variants...")
        except Exception:
            pass
        
        # بررسی همه کلیدها - normalize کردن هر کلید و مقایسه
        for key in data.keys():
            normalized_key = _normalize_user_id(key)
            if normalized_key == normalized_user_id:
                found_items = data.get(key, [])
                if found_items:
                    items = found_items
                    try:
                        current_app.logger.info(f"Found notifications with variant key '{key}' (normalizes to '{normalized_key}')")
                    except Exception:
                        pass
                    break
    
    # Logging
    try:
        current_app.logger.info(
            f"Returning {len(items)} notifications for user_id={normalized_user_id}"
        )
    except Exception:
        pass
    
    # محدود کردن تعداد
    limit = max(1, int(limit or 50))
    return items[:limit]


def unread_count(user_id: str) -> int:
    """شمارش اعلان‌های خوانده نشده"""
    notifications = get_user_notifications(user_id, limit=9999)
    return sum(1 for n in notifications if not n.get("is_read", False))


def mark_read(user_id: str, notif_id: str) -> bool:
    """علامت‌گذاری یک اعلان به عنوان خوانده شده"""
    if not user_id or not notif_id:
        return False
    
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return False
    
    data = _load_all()
    items = data.get(normalized_user_id, [])
    
    if not isinstance(items, list):
        return False
    
    found = False
    for n in items:
        if n.get("id") == notif_id:
            n["is_read"] = True
            found = True
            break
    
    if found:
        _save_all(data)
        try:
            current_app.logger.info(f"Notification marked as read: user_id={normalized_user_id}, notif_id={notif_id}")
        except Exception:
            pass
    
    return found


def mark_all_read(user_id: str) -> int:
    """علامت‌گذاری همه اعلان‌های یک کاربر به عنوان خوانده شده"""
    if not user_id:
        return 0
    
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return 0
    
    data = _load_all()
    items = data.get(normalized_user_id, [])
    
    if not isinstance(items, list):
        return 0
    
    count = 0
    for n in items:
        if not n.get("is_read", False):
            n["is_read"] = True
            count += 1
    
    if count > 0:
        _save_all(data)
        try:
            current_app.logger.info(f"Marked {count} notifications as read for user_id={normalized_user_id}")
        except Exception:
            pass
    
    return count


def get_all_notifications_stats() -> Dict[str, Any]:
    """دریافت آمار کلی اعلان‌ها (برای ادمین)"""
    data = _load_all()
    total_users = len(data)
    total_notifications = sum(len(items) for items in data.values() if isinstance(items, list))
    total_unread = 0
    
    for items in data.values():
        if isinstance(items, list):
            total_unread += sum(1 for n in items if not n.get("is_read", False))
    
    return {
        "total_users": total_users,
        "total_notifications": total_notifications,
        "total_unread": total_unread
    }
