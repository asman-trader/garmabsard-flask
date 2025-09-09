# -*- coding: utf-8 -*-
"""
Vinor Notifications Service (JSON-based)
"""
import json, os, time, uuid
from typing import List, Dict, Any

DATA_DIR = os.path.join("app", "data")
FILE_PATH = os.path.join(DATA_DIR, "notifications.json")
BACKUP_PATH = os.path.join(DATA_DIR, "notifications.backup.json")


def _ensure_store():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def _normalize_loaded(raw) -> Dict[str, List[Dict[str, Any]]]:
    """
    ورودی ممکنه dict یا list باشه. این تابع هر چیزی رو به ساختار استاندارد:
    { user_id: [ {notif}, ... ] } تبدیل می‌کنه.
    """
    # حالت سالم
    if isinstance(raw, dict):
        fixed: Dict[str, List[Dict[str, Any]]] = {}
        for k, v in raw.items():
            if isinstance(v, list):
                # فقط آیتم‌های دیکشنری نگه‌داری بشن
                fixed[k] = [n for n in v if isinstance(n, dict)]
            else:
                fixed[k] = []
        return fixed

    # حالت قدیمی/خراب: لیست تخت از اعلان‌ها
    if isinstance(raw, list):
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for n in raw:
            if not isinstance(n, dict):
                continue
            uid = n.get("user_id") or n.get("uid")  # اگر قبلاً فیلد user_id ذخیره شده
            if uid:
                grouped.setdefault(uid, []).append(n)
        return grouped  # ممکنه خالی باشد

    # هر چیز دیگر → خالی
    return {}

def _load() -> Dict[str, List[Dict[str, Any]]]:
    _ensure_store()
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        # فایل خراب → ریست
        try:
            if os.path.exists(FILE_PATH):
                os.replace(FILE_PATH, BACKUP_PATH)  # بکاپ
        except Exception:
            pass
        return {}

    data = _normalize_loaded(raw)

    # اگر ساختار اصلاح شد، بازنویسی کن تا برای دفعات بعدی سالم باشه
    try:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return data

def _save(data: Dict[str, List[Dict[str, Any]]]):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_notification(user_id: str, title: str, body: str, ntype: str = "info",
                     ad_id: str | None = None, action_url: str | None = None) -> Dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")

    data = _load()
    notif = {
        "id": str(uuid.uuid4()),
        "title": title,
        "body": body,
        "type": ntype,  # info | success | warning | error | status
        "created_at": int(time.time()),
        "is_read": False,
        "ad_id": ad_id,
        "action_url": action_url,
        # (اختیاری) برای سازگاری با نسخه‌های قدیمی:
        "user_id": user_id,
    }
    data.setdefault(user_id, []).insert(0, notif)
    _save(data)
    return notif

def get_user_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    if not user_id:
        return []
    data = _load()
    items = data.get(user_id, [])
    if not isinstance(items, list):
        return []
    return items[: max(1, int(limit or 1))]

def unread_count(user_id: str) -> int:
    return sum(1 for n in get_user_notifications(user_id, 9999) if not n.get("is_read"))

def mark_read(user_id: str, notif_id: str) -> bool:
    if not user_id or not notif_id:
        return False
    data = _load()
    arr = data.get(user_id, [])
    ok = False
    if isinstance(arr, list):
        for n in arr:
            if n.get("id") == notif_id:
                n["is_read"] = True
                ok = True
                break
    if ok:
        _save(data)
    return ok

def mark_all_read(user_id: str) -> int:
    if not user_id:
        return 0
    data = _load()
    arr = data.get(user_id, [])
    c = 0
    if isinstance(arr, list):
        for n in arr:
            if not n.get("is_read"):
                n["is_read"] = True
                c += 1
        _save(data)
    return c
