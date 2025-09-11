# -*- coding: utf-8 -*-
"""
Root-level Admin package
- Defines `admin_bp` blueprint
- Loads route modules in a decentralized way for easier maintenance
"""

from .blueprint import admin_bp  # blueprint definition and template_folder setup

# Attach route modules (side-effect imports register routes on admin_bp)
from . import routes  # core/admin basics, lands, settings, consults, auth (existing)
try:
    from . import sms_campaign  # sms campaign page
except Exception:
    pass
try:
    from . import push_pages  # push test page
except Exception:
    pass

__all__ = ["admin_bp"]

