import subprocess
from flask import Blueprint, request

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/git-webhook', methods=['POST'])
def git_webhook():
    event = request.headers.get('X-GitHub-Event')
    if event != 'push':
        return '❌ Unsupported event', 400

    try:
        # مسیر واقعی پروژه روی سرور
        project_path = '/home/garmabs2/myapp'

        # اجرای git pull
        subprocess.Popen(['git', '-C', project_path, 'pull'])
        return '✅ Git pull triggered successfully.', 200

    except Exception as e:
        return f'❌ Error during git pull: {str(e)}', 500
