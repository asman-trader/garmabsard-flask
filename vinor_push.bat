@echo off
setlocal enabledelayedexpansion

rem حرکت به مسیر اسکریپت (پرتابل)
cd /d "%~dp0"

rem اطمینان از اینکه داخل مخزن گیت هستیم
git rev-parse --is-inside-work-tree >nul 2>&1 || (
  echo این مسیر یک مخزن Git نیست.
  pause
  exit /b 1
)

rem شاخه فعلی را تشخیص بده
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if "%BRANCH%"=="" set BRANCH=main

rem جلوگیری از استیج‌شدن فایل‌های حساس/داده
git restore --staged app/data instance uploads logs app/static/uploads app/data/uploads *.db *.sqlite* *.log .env .env.* *.pem *.key *.crt >nul 2>&1

rem به‌روزرسانی مخزن با rebase (در صورت نیاز autostash)
git pull --rebase --autostash origin %BRANCH%

rem استیج همه تغییرات
git add -A

rem دوباره فایل‌های حساس را از استیج خارج کن
git reset app/data instance uploads logs app/static/uploads app/data/uploads *.db *.sqlite* *.log .env .env.* *.pem *.key *.crt >nul 2>&1

rem اگر چیزی برای کامیت نیست
git diff --cached --quiet && (
  echo هیچ تغییری برای پوش نیست.
  pause
  exit /b 0
)

rem نسخه‌گذاری ساده – اگر نبود، بساز
set version=0
if exist version.txt set /p version=<version.txt
for /f "delims=0123456789" %%x in ("%version%") do set version=0
set /a version+=1
echo %version%>version.txt
git add version.txt

rem پیام کامیت – اگر پارامتر ورودی بود، همان را استفاده کن
set msg=
if not "%~1"=="" (
  set msg=%*
) else (
  set msg=Auto commit v%version%
)

rem نمایش خلاصه تغییرات
echo --------------------------
git status --short
echo --------------------------

rem کامیت و پوش به شاخه فعلی
git commit -m "%msg%"
git push origin %BRANCH%

echo --------------------------
echo ✅ %msg% روی شاخه %BRANCH% پوش شد.
pause
