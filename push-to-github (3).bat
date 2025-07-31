@echo off
setlocal

:: تنظیم مسیر پروژه (حتماً همین مسیر رو نگه‌دار یا تغییر بده به پوشه خودت)
cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

:: بررسی اینکه git نصب هست یا نه
git --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Git نصب نیست یا در مسیر PATH نیست.
    pause
    exit /b
)

:: نمایش وضعیت
echo --------------------------
echo وضعیت فعلی پروژه:
git status
echo --------------------------

:: دریافت پیام کامیت
set /p msg=لطفاً پیام تغییرات را وارد کن:

git add .
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ✅ تغییرات با موفقیت ارسال شد.
pause
