import sys
import os

# مسیر پروژه شما
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# فعال‌سازی محیط مجازی
activate_this = '/home/garmabs2/virtualenv/myapp/3.11/bin/activate_this.py'
if os.path.exists(activate_this):
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))

# اجرای اپ Flask
try:
    from app import create_app
    application = create_app()
except Exception as e:
    # در صورت بروز خطا، پیام مناسب برگردان
    def application(environ, start_response):
        status = '500 INTERNAL SERVER ERROR'
        output = f'Error loading application: {str(e)}'.encode()
        response_headers = [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]
