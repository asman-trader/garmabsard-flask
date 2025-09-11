from flask import Blueprint

# Single place to own the blueprint config
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')


