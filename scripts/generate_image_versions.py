import os
from PIL import Image

# مسیر اصلی تصاویر
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'uploads'))
THUMB_DIR = os.path.join(BASE_DIR, 'thumbs')

# ایجاد پوشه thumbs در صورت نیاز
os.makedirs(THUMB_DIR, exist_ok=True)

# تنظیمات اندازه تصویر بندانگشتی
THUMB_SIZE = (400, 400)  # قابل تغییر

# پسوندهای مجاز تصویر
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

def is_image_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def generate_thumbnail(filename):
    input_path = os.path.join(BASE_DIR, filename)
    output_path = os.path.join(THUMB_DIR, filename)

    # اگر قبلاً ساخته شده، رد شو
    if os.path.exists(output_path):
        print(f'✅ موجود است: {filename}')
        return

    try:
        with Image.open(input_path) as img:
            img.thumbnail(THUMB_SIZE)
            img.save(output_path)
            print(f'✅ ساخته شد: {filename}')
    except Exception as e:
        print(f'❌ خطا در پردازش {filename}: {e}')

def process_all_images():
    for filename in os.listdir(BASE_DIR):
        if is_image_file(filename):
            generate_thumbnail(filename)

if __name__ == '__main__':
    print("🔄 شروع پردازش تصاویر...")
    process_all_images()
    print("✅ همه تصاویر پردازش شدند.")
