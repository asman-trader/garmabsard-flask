# app/routes/__init__.py
from flask import Blueprint
from ..utils.storage import ensure_file, migrate_legacy

main_bp = Blueprint("main", __name__)

# روت‌ها باید قبل از register شدن لود شوند
from . import public, auth, ads, profile, notifications, diagnostics  # noqa: F401

@main_bp.record_once
def _bootstrap(state):
    app = state.app
    migrate_legacy(app)
    ensure_file('LANDS_FILE','lands.json',[],app)
    ensure_file('USERS_FILE','users.json',[],app)
    ensure_file('CONSULTS_FILE','consults.json',[],app)
    ensure_file('SETTINGS_FILE','settings.json',{"approval_method":"manual"},app)
    ensure_file('NOTIFICATIONS_FILE','notifications.json',[],app)
