# app/api/push.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from typing import List, Dict, Any
from flask import Blueprint, current_app, request, jsonify

# اگر pywebpush ندارید: pip install pywebpush cryptography
try:
    from pywebpush import webpush, WebPushException
except Exception:
    webpush = None
    WebPushException = Exception  # fallback برای import

api_push_bp = Blueprint('api_push', __name__, url_prefix='/api/push')

# -------------------------------
# مسیر فایل سابسکرایب‌ها
# -------------------------------
def _subs_path() -> str:
    base = current_app.instance_path
    path = os.path.join(base, 'data', 'push_subs.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def _load_subs() -> List[Dict[str, Any]]:
    path = _subs_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def _save_subs(subs: List[Dict[str, Any]]) -> None:
    path = _subs_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)

# این توابع را ادمین برای تست هم استفاده می‌کند
def _send_one(subscription: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    if webpush is None:
        return {'ok': False, 'error': 'PYWEBPUSH_NOT_INSTALLED', 'remove': False}

    vapid_private = current_app.config.get('VAPID_PRIVATE_KEY', '')
    vapid_claims = {'sub': current_app.config.get('VAPID_CLAIMS_SUB', 'mailto:support@vinor.ir')}
    if not vapid_private:
        return {'ok': False, 'error': 'MISSING_VAPID_PRIVATE_KEY', 'remove': False}

    try:
        # WebPush standard payload (data is string). Some browsers expect 'notification' wrapper.
        data_str = json.dumps(payload, ensure_ascii=False)
        webpush(
            subscription_info=subscription,
            data=data_str,
            vapid_private_key=vapid_private,
            vapid_claims=vapid_claims,
            timeout=10
        )
        return {'ok': True}
    except WebPushException as e:
        status = getattr(e.response, 'status_code', None)
        if status in (404, 410):
            return {'ok': False, 'error': f'STATUS_{status}', 'remove': True}
        return {'ok': False, 'error': str(e), 'remove': False}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'remove': False}

# -------------------------------
# API: دریافت کلید عمومی
# -------------------------------
@api_push_bp.get('/config')
def push_config():
    return jsonify({'publicKey': current_app.config.get('VAPID_PUBLIC_KEY', '')})

# -------------------------------
# API: Subscribe (بدنه: آبجکت خام PushSubscription)
# -------------------------------
@api_push_bp.post('/subscribe')
def subscribe():
    try:
        sub = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({'ok': False, 'error': 'INVALID_JSON'}), 400

    if not isinstance(sub, dict) or 'endpoint' not in sub:
        return jsonify({'ok': False, 'error': 'INVALID_SUBSCRIPTION'}), 400

    subs = _load_subs()
    endpoint = sub.get('endpoint')

    idx = next((i for i, s in enumerate(subs) if s.get('endpoint') == endpoint), None)
    if idx is not None:
        subs[idx] = sub
    else:
        subs.append(sub)

    _save_subs(subs)
    return jsonify({'ok': True, 'count': len(subs)})

# -------------------------------
# API: Unsubscribe (body: {"endpoint": "..."})
# -------------------------------
@api_push_bp.post('/unsubscribe')
def unsubscribe():
    data = request.get_json(force=True, silent=True) or {}
    endpoint = data.get('endpoint')
    if not endpoint:
        return jsonify({'ok': False, 'error': 'MISSING_ENDPOINT'}), 400

    subs = _load_subs()
    subs = [s for s in subs if s.get('endpoint') != endpoint]
    _save_subs(subs)
    return jsonify({'ok': True, 'count': len(subs)})

# -------------------------------
# دیباگ: شمار مشترک‌ها
# -------------------------------
@api_push_bp.get('/subs')
def list_subs():
    subs = _load_subs()
    return jsonify({'ok': True, 'count': len(subs)})

# -------------------------------
# سازگاری عقب‌رو (alias)
# برخی بخش‌های پروژه ممکن است push_bp را import کنند.
# -------------------------------
push_bp = api_push_bp
__all__ = ['api_push_bp', 'push_bp', '_load_subs', '_save_subs', '_send_one']
