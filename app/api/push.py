# app/api/push.py
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, abort
from pywebpush import webpush, WebPushException

push_bp = Blueprint("push_bp", __name__)

# ---- Helpers: STORE path should be resolved at runtime (no current_app at import) ----
def _store_path() -> Path:
    """
    مسیر ذخیره اشتراک‌ها:
    - اگر در کانفیگ PUSH_STORE_PATH تعریف شده باشد، همان استفاده می‌شود.
    - در غیر اینصورت: [project_root]/data/push_subs.json
      (project_root با استفاده از موقعیت همین فایل به‌صورت امن محاسبه می‌شود)
    """
    cfg_path = current_app.config.get("PUSH_STORE_PATH")
    if cfg_path:
        return Path(cfg_path)

    # project root = .../G  (دو پوشه بالاتر از app/api/push.py)
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "data" / "push_subs.json"


def _load_subs():
    store = _store_path()
    if store.exists():
        try:
            return json.loads(store.read_text("utf-8"))
        except Exception:
            return []
    return []


def _save_subs(data):
    store = _store_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@push_bp.route("/api/push/subscribe", methods=["POST"])
def subscribe():
    sub = request.get_json(silent=True)
    if not sub or "endpoint" not in sub:
        return abort(400, "invalid subscription")

    subs = _load_subs()
    if not any(s.get("endpoint") == sub["endpoint"] for s in subs):
        subs.append(sub)
        _save_subs(subs)
    return jsonify({"ok": True, "count": len(subs)})


@push_bp.route("/api/push/unsubscribe", methods=["POST", "DELETE"])
def unsubscribe():
    sub = request.get_json(silent=True)
    if not sub or "endpoint" not in sub:
        return abort(400, "invalid subscription")
    subs = _load_subs()
    subs = [s for s in subs if s.get("endpoint") != sub["endpoint"]]
    _save_subs(subs)
    return jsonify({"ok": True, "count": len(subs)})


@push_bp.route("/api/push/test", methods=["POST"])
def push_test():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", "وینور")
    body  = payload.get("body", "اعلان تستی")
    url   = payload.get("url", "/app")

    data = {
        "title": title,
        "body": body,
        "icon": "/static/icons/icon-72.png",
        "badge": "/static/icons/icon-72.png",
        "data": {"url": url},
        "actions": [{"action": "open", "title": "باز کردن"}],
    }

    subs = _load_subs()
    vapid_public  = current_app.config.get("VAPID_PUBLIC_KEY")
    vapid_private = current_app.config.get("VAPID_PRIVATE_KEY")
    vapid_claims  = current_app.config.get("VAPID_CLAIMS", {"sub": "mailto:admin@vinor.ir"})

    if not vapid_public or not vapid_private:
        return abort(500, "VAPID keys not configured")

    sent, failed = 0, 0
    keep = []

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(data, ensure_ascii=False),
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
            )
            keep.append(sub)
            sent += 1
        except WebPushException:
            failed += 1  # endpoint نامعتبر؛ حذف در پایان

    _save_subs(keep)
    return jsonify({"ok": True, "sent": sent, "failed": failed, "active": len(keep)})
