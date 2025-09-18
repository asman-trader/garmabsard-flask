# app/routes/diagnostics.py
import os, subprocess
from datetime import datetime
from flask import current_app, render_template
from . import main_bp
from ..utils.storage import data_dir, load_ads

@main_bp.route('/healthz')
def healthz():
    try:
        _ = load_ads()
        return "ok", 200
    except Exception as e:
        try: current_app.logger.exception("Health error: %s", e)
        except Exception: pass
        return "not ok", 500

@main_bp.route('/diag')
def diag():
    info = {}
    try:
        app = current_app
        info['instance_path'] = app.instance_path
        d = data_dir()
        info['data_dir'] = d
        info['writable'] = os.access(d, os.W_OK)
        tf = os.path.join(d, '.__write_test')
        with open(tf,'w',encoding='utf-8') as f: f.write(datetime.now().isoformat())
        os.remove(tf)
        info['write_test'] = 'ok'
    except Exception as e:
        info['write_test'] = f'error: {e}'
    return info, 200


# صفحه بررسی اتصال اینترنت (PWA)
@main_bp.route('/connection')
def connection_check():
    return render_template('connection.html')
