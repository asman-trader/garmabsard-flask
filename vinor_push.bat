@echo off
cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

:: جلوگیری از پوش شدن فایل‌های دیتایی
git restore --staged app/data instance uploads logs *.db *.sqlite *.log .env >nul 2>&1

:: آخرین تغییرات رو بکش
git pull --rebase

:: همه فایل‌ها رو استیج کن
git add -A

:: فایل‌های دیتایی رو دوباره از استیج دربیار
git reset app/data instance uploads logs *.db *.sqlite *.log .env >nul 2>&1

:: اگر چیزی برای کامیت نیست
git diff --cached --quiet && (
    echo هیچ تغییری برای پوش نیست.
    pause
    exit /b
)

:: نسخه
set version=0
if exist version.txt set /p version=<version.txt
set /a version+=1
echo %version%>version.txt
git add version.txt

:: پیام کامیت
set msg=Auto commit v%version%

git commit -m "%msg%"
git push origin main

echo --------------------------
echo ✅ %msg% پوش شد.
pause
