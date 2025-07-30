import sys
import os

# مسیر پروژه رو به sys.path اضافه کن
sys.path.insert(0, os.path.dirname(__file__))

# ساخت و اجرای اپ Flask
from app import create_app
application = create_app()
