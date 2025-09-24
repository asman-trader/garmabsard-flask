@echo off
setlocal enabledelayedexpansion

rem ===== حرکت به مسیر اسکریپت (پرتابل) =====
cd /d "%~dp0"

rem ===== اطمینان از اینکه داخل مخزن گیت هستیم =====
git rev-parse --is-inside-work-tree >nul 2>&1 || (
  echo این مسیر یک مخزن Git نیست.
  pause
  exit /b 1
)

rem ===== بررسی و حل rebase نیمه‌تمام =====
if exist ".git/rebase-merge" (
    echo Rebase نیمه‌تمام پیدا شد، با دستور abort آن را پاک می‌کنیم...
    git rebase --abort
)

rem ===== شاخه فعلی را تشخیص بده =====
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if "%BRANCH%"=="" set BRANCH=main
echo شاخه فعلی: %BRANCH%

rem ===== جلوگیری از استیج‌شدن فایل‌های حساس/داده =====
set EXCLUDE=app/data instance uploads logs app/static/uploads app/data/uploads *.db *.sqlite* *.log .env .env.* *.pem *.key *.crt

git restore --staged %EXCLUDE% >nul 2>&1

rem ===== به‌روزرسانی مخزن با rebase (autostash) =====
git pull --rebase --autostash https://github.com/asman-trader/garmabsard-flask.git %BRANCH%

rem ===== استیج همه تغییرات =====
git add -A

rem ===== دوباره فایل‌های حساس را از استیج خارج کن =====
git reset %EXCLUDE% >nul 2>&1

rem ===== اگر چیزی برای کامیت نیست =====
git diff --cached --quiet && (
  echo هیچ تغییری برای پوش نیست.
  pause
  exit /b 0
)

rem ===== نسخه‌گذاری ساده – اگر نبود، بساز =====
set version=0
if exist version.txt set /p version=<version.txt
for /f "delims=0123456789" %%x in ("%version%") do set version=0
set /a version+=1
echo %version%>version.txt
git add version.txt

rem ===== پیام کامیت – اگر پارامتر ورودی بود، همان را استفاده کن =====
set msg=
if not "%~1"=="" (
  set msg=%*
) else (
  set msg=Auto commit v%version%
)

rem ===== نمایش خلاصه تغییرات =====
echo --------------------------
git status --short
echo --------------------------

rem ===== کامیت و پوش به ریپوی GitHub =====
git commit -m "%msg%"

rem ===== push امن با HTTPS =====
git push https://github.com/asman-trader/garmabsard-flask.git %BRANCH% --force

echo --------------------------
echo ✅ %msg% روی شاخه %BRANCH% در GitHub پوش شد.
pause
