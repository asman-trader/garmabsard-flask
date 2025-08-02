import subprocess
from flask import Blueprint, request

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/git-webhook', methods=['POST'])
def git_webhook():
    event = request.headers.get('X-GitHub-Event')
    if event != 'push':
        return '❌ Unsupported event', 400

    try:
        # مسیر پروژه خودت رو اینجا وارد کن
        project_path = '/path/to/your/project'

        subprocess.Popen(['git', '-C', project_path, 'pull'])
        return '✅ Git pull triggered', 200
    except Exception as e:
        return f'❌ Error: {str(e)}', 500
