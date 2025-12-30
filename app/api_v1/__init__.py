from __future__ import annotations

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api")

# Register route modules (import side-effects)
from . import auth  # noqa: F401
from . import ads  # noqa: F401
from . import favorites  # noqa: F401
from . import consultations  # noqa: F401
from . import openapi  # noqa: F401
from . import dev  # noqa: F401


