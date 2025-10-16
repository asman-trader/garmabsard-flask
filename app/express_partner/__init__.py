from flask import Blueprint

express_partner_bp = Blueprint(
    'express_partner', __name__,
    url_prefix='/express/partner',
    template_folder='templates'
)

from . import routes  # noqa: F401


