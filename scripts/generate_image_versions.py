import os
from PIL import Image

# مسیر کامل به پوشه پروژه
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, 'app', 'data', 'uploads')
VERSIONS = {
    'thumb': (200, 200),
    'medium': (800, 600),
    'large': (1600, 1200)
}

def generate_versions(image_path, filename):
    try:
        img = Image.open(image_path)
        for version, size in VERSIONS.items():
            folder = os.path.join(UPLOAD_DIR, version)
            os.makedirs(folder, exist_ok=True)
            version_path = os.path.join(folder, filename)
            img_copy = img.copy()
            img_copy.thumbnail(size)
            img_copy.save(version_path, optimize=True)
            print(f"✅ {version} ساخته شد: {version_path}")
    except Exception as e:
        print(f"❌ خطا در پردازش {filename}: {e}")

def process_all_images():
    if not os.path.exists(UPLOAD_DIR):
        print(f"❌ مسیر پیدا نشد: {UPLOAD_DIR}")
        return

    for filename in os.listdir(UPLOAD_DIR):
        full_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(full_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            generate_versions(full_path, filename)

if __name__ == '__main__':
    process_all_images()
