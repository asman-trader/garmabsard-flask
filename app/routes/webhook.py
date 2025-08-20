# -*- coding: utf-8 -*-
"""
Webhook امن و پایدار برای دیپلوی خودکار از GitHub.
- فقط روی رویداد push
- (اختیاری) تأیید امضا با X-Hub-Signature-256 اگر SECRET پر باشد
- فیلتر برنچ (پیش‌فرض: main)
- دیپلوی: git fetch --all --prune → git reset --hard origin/<branch> → git clean -fd (با استثنا برای instance/)
- (اختیاری) اجرای دستورات پس از دیپلوی (مثلاً ری‌استارت سرویس)
"""
import os, hmac, hashlib, shlex, subprocess
from typing import List, Tuple, Dict, Any
from flask import Blueprint, request, jsonify

# ───────────── تنظیمات (طبق سرورت تنظیم کن) ─────────────
PROJECT_PATH = "/home/garmabs2/myapp"
ALLOWED_BRANCHES = {"main"}            # برنچ‌های مجاز
SECRET = ""                            # اگر ست شود، امضا چک می‌شود (GitHub → Webhook → Secret)
POST_DEPLOY_COMMANDS: List[str] = [
    # مثال‌ها (دلخواه):
    # "systemctl --user restart garmabsard.service",
    # "sudo systemctl restart garmabsard",
]

# ───────────── هِلپرها ─────────────
def run(cmd: str, cwd: str = None, timeout: int = 180) -> Dict[str, Any]:
    """اجرای امن دستور و بازگرداندن rc/out/err."""
    proc = subprocess.run(
        shlex.split(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }

def verify_signature(secret: str, raw_body: bytes) -> bool:
    """تأیید HMAC-SHA256 امضای GitHub (X-Hub-Signature-256)."""
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not secret:
        return True  # اگر Secret خالیست، چک نکن (برای تست)
    if not sig.startswith("sha256="):
        return False
    sent = sig.split("=", 1)[1].strip()
    mac = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sent)

def extract_branch(ref: str) -> str:
    # ref مثل "refs/heads/main"
    return ref.split("/", 2)[-1] if ref and ref.startswith("refs/heads/") else ""

# ───────────── Blueprint ─────────────
webhook_bp = Blueprint("webhook", __name__)

@webhook_bp.route("/git-webhook", methods=["POST"])
def git_webhook():
    # 1) رویداد
    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return jsonify(ok=True, pong=True), 200
    if event != "push":
        return jsonify(ok=False, error="Unsupported event", event=event), 400

    # 2) امضا
    raw = request.get_data()  # مهم: raw body برای HMAC
    if not verify_signature(SECRET, raw):
        return jsonify(ok=False, error="Invalid signature"), 403

    # 3) payload و برنچ
    payload = request.get_json(silent=True) or {}
    ref = payload.get("ref", "")
    branch = extract_branch(ref)
    if not branch:
        return jsonify(ok=False, error="Invalid ref", ref=ref), 400
    if branch not in ALLOWED_BRANCHES:
        return jsonify(ok=True, skipped=True, reason="Branch not allowed", ref=ref), 200

    # 4) اعتبار مسیر و ریپو
    if not PROJECT_PATH or not os.path.isdir(PROJECT_PATH):
        return jsonify(ok=False, error="Project path not found", path=PROJECT_PATH), 500

    steps: List[Dict[str, Any]] = []

    # چک گیت بودن
    steps.append(run("git rev-parse --is-inside-work-tree", cwd=PROJECT_PATH))
    if steps[-1]["rc"] != 0 or steps[-1]["stdout"] != "true":
        return jsonify(ok=False, step="check-git", results=steps), 500

    # 5) دیپلوی بدون Merge: fetch → reset → clean
    for cmd in [
        "git fetch --all --prune",
        f"git reset --hard origin/{branch}",
        # instance را دست نزن
        "git clean -fd -e instance -e instance/*",
    ]:
        steps.append(run(cmd, cwd=PROJECT_PATH))
        if steps[-1]["rc"] != 0:
            return jsonify(ok=False, step="git", results=steps), 500

    # 6) دستورات پس از دیپلوی (دلخواه)
    for cmd in POST_DEPLOY_COMMANDS:
        steps.append(run(cmd, cwd=PROJECT_PATH))
        if steps[-1]["rc"] != 0:
            return jsonify(ok=False, step="post_deploy", results=steps), 500

    return jsonify(ok=True, branch=branch, results=steps), 200
