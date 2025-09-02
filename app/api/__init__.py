# -*- coding: utf-8 -*-
"""
Make app.api a proper Python package and expose optional blueprints.
"""

# اختیاری: اگر یکی از این فایل‌ها نبود، ایمپورت خطا نده
try:
    from .uploads import uploads_bp  # /api/uploads/images , /uploads/...
except Exception:
    uploads_bp = None

try:
    from .push import push_bp        # /api/push/*
except Exception:
    push_bp = None

__all__ = ["uploads_bp", "push_bp"]
