# -*- coding: utf-8 -*-
import os, hmac, hashlib, shlex, subprocess, fcntl, time, json
from typing import List, Dict, Any
from flask import Blueprint, request, jsonify

# ───────── کانفیگ از Env (ایمن‌تر) ─────────
PROJECT_PATH = os.getenv("VINOR_PROJECT_PATH", "/home/garmabs2/myapp")
ALLOWED_BRANCHES = set(os.getenv("VINOR_ALLOWED_BRANCHES", "main").split(","))
SECRET = os.getenv("VINOR_WEBHOOK_SECRET", "")  # در GitHub هم همین Secret
ALLOWED_REPO = os.getenv("VINOR_ALLOWED_REPO", "asman-trader/garmabsard-flask")  # owner/repo
DEPLOY_LOG = os.getenv("VINOR_DEPLOY_LOG", f"{PROJECT_PATH}/deploy.log")
LOCK_FILE = os.getenv("VINOR_DEPLOY_LOCK", "/tmp/vinor_deploy.lock")
TIMEOUT = int(os.getenv("VINOR_CMD_TIMEOUT", "300"))

# دستورات پسادیپلوی (Passenger/venv)
VENV_ACTIVATE = "/home/garmabs2/virtualenv/myapp/3.11/bin/activate"
POST_DEPLOY_COMMANDS: List[str] = [
    # نصب وابستگی‌ها اگر وجود داشت
    f"bash -lc 'source {shlex.quote(VENV_ACTIVATE)} && pip install --upgrade pip && "
    f"[ -f requirements.txt ] && pip install -r requirements.txt || true'",
    # Passenger restart
    "bash -lc 'mkdir -p tmp && touch tmp/restart.txt'",
]

webhook_bp = Blueprint("webhook", __name__)

def log_line(msg: str, extra: Dict[str, Any] = None) -> None:
    try:
        rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "msg": msg}
        if extra: rec.update(extra)
        with open(DEPLOY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

def run(cmd: str, cwd: str = None, timeout: int = TIMEOUT) -> Dict[str, Any]:
    proc = subprocess.run(
        shlex.split(cmd), cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    out = {"cmd": cmd, "rc": proc.returncode,
           "stdout": (proc.stdout or "").strip(), "stderr": (proc.stderr or "").strip()}
    log_line("run", out)
    return out

def verify_signature(secret: str, raw_body: bytes) -> bool:
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not secret:  # برای تست/استیجینگ
        return True
    if not sig.startswith("sha256="):
        return False
    sent = sig.split("=", 1)[1].strip()
    mac = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sent)

def extract_branch(ref: str) -> str:
    return ref.split("/", 2)[-1] if ref and ref.startswith("refs/heads/") else ""

def acquire_lock() -> Any:
    f = open(LOCK_FILE, "w+")
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    f.write(str(time.time()))
    f.flush()
    return f

@webhook_bp.route("/git-webhook", methods=["POST"])
def git_webhook():
    event = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    if event == "ping":
        return jsonify(ok=True, pong=True), 200
    if event != "push":
        return jsonify(ok=False, error="Unsupported event", event=event), 400

    raw = request.get_data()
    if not verify_signature(SECRET, raw):
        log_line("invalid_signature", {"delivery": delivery_id})
        return jsonify(ok=False, error="Invalid signature"), 403

    payload = request.get_json(silent=True) or {}
    repo_full = (payload.get("repository") or {}).get("full_name", "")
    if ALLOWED_REPO and repo_full != ALLOWED_REPO:
        log_line("repo_not_allowed", {"got": repo_full, "want": ALLOWED_REPO})
        return jsonify(ok=True, skipped=True, reason="Repo not allowed", repo=repo_full), 200

    ref = payload.get("ref", "")
    branch = extract_branch(ref)
    if not branch:
        return jsonify(ok=False, error="Invalid ref", ref=ref), 400
    if branch not in ALLOWED_BRANCHES:
        return jsonify(ok=True, skipped=True, reason="Branch not allowed", ref=ref), 200

    if not PROJECT_PATH or not os.path.isdir(PROJECT_PATH):
        return jsonify(ok=False, error="Project path not found", path=PROJECT_PATH), 500

    # جلوگیری از دیپلوی هم‌زمان
    try:
        lock_handle = acquire_lock()
    except BlockingIOError:
        log_line("deploy_locked", {"delivery": delivery_id})
        return jsonify(ok=True, skipped=True, reason="Another deploy in progress"), 200

    steps: List[Dict[str, Any]] = []
    try:
        steps.append(run("git rev-parse --is-inside-work-tree", cwd=PROJECT_PATH))
        if steps[-1]["rc"] != 0 or steps[-1]["stdout"] != "true":
            return jsonify(ok=False, step="check-git", results=steps), 500

        for cmd in [
            "git config --global --add safe.directory " + PROJECT_PATH,
            "git fetch --all --prune",
            f"git reset --hard origin/{branch}",
            "git clean -fd -e instance -e instance/*",
        ]:
            steps.append(run(cmd, cwd=PROJECT_PATH))
            if steps[-1]["rc"] != 0:
                return jsonify(ok=False, step="git", results=steps), 500

        for cmd in POST_DEPLOY_COMMANDS:
            steps.append(run(cmd, cwd=PROJECT_PATH))
            if steps[-1]["rc"] != 0:
                return jsonify(ok=False, step="post_deploy", results=steps), 500

        log_line("deploy_ok", {"branch": branch, "delivery": delivery_id})
        return jsonify(ok=True, branch=branch, results=steps), 200

    finally:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_UN)
            lock_handle.close()
        except Exception:
            pass
