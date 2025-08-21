# run.py
import os, logging
from logging.handlers import RotatingFileHandler
from flask import send_from_directory, request, jsonify
from app import create_app

app = create_app()

def _setup_logging(flask_app):
    try:
        logs_dir = os.path.join(flask_app.instance_path, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        fh = RotatingFileHandler(os.path.join(logs_dir,"app.log"), maxBytes=2*1024*1024, backupCount=5, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        flask_app.logger.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in flask_app.logger.handlers):
            flask_app.logger.addHandler(fh)
    except Exception as e:
        print("Log setup error:", e)
_setup_logging(app)

@app.route("/favicon.ico")
def _favicon():
    static_dir = os.path.join(app.root_path, "static")
    path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(path):
        return send_from_directory(static_dir, "favicon.ico")
    return ("", 204)

@app.errorhandler(404)
def _nf(e):
    if request.path.startswith("/static/"): return ("", 404)
    return jsonify({"error":"Not Found","path":request.path}), 404

if __name__ == "__main__":
    app.run(debug=True, host=os.environ.get("FLASK_RUN_HOST","0.0.0.0"), port=int(os.environ.get("FLASK_RUN_PORT","5000")))
