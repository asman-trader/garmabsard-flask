# -*- coding: utf-8 -*-
"""
Root-level Admin package
- Exposes admin_bp blueprint
- Routes are defined in admin.routes
"""

from .routes import admin_bp  # re-export for app factory

__all__ = ["admin_bp"]


